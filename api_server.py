"""
FastAPI server for desktop automation AI that can receive prompts through REST API endpoints.
This server runs alongside the Streamlit app and provides programmatic access to the AI agent.
"""

import asyncio
import os
import traceback
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from functools import partial

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import RateLimitError
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaTextBlockParam,
)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    pass

from loop import (
    PROVIDER_TO_DEFAULT_MODEL_NAME,
    APIProvider,
    sampling_loop,
)
from tools import ToolResult
from utils.assembly_media_service import download_media_from_assembly

app = FastAPI(
    title="Desktop Automation AI API",
    description="REST API for Claude Windows Computer Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Sender(StrEnum):
    USER = "user"
    BOT = "assistant"
    TOOL = "tool"

# Global state for the API server
class APIState:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.provider: APIProvider = APIProvider.ANTHROPIC
        self.model: str = PROVIDER_TO_DEFAULT_MODEL_NAME[self.provider]
        self.responses: Dict[str, Any] = {}
        self.tools: Dict[str, ToolResult] = {}
        self.only_n_most_recent_images: int = 10
        self.custom_system_prompt: str = ""
        self.hide_images: bool = False
        self.auth_validated: bool = False
        self.is_processing: bool = False
        self.downloaded_files: List[str] = []  # Track downloaded file paths
        self.desktop_path: str = r"C:\Users\ahmad\Desktop"
        self.current_task_folder: str = ""  # Will be set per task
        
    def reset(self):
        """Reset the state for a new session"""
        self.messages = []
        self.responses = {}
        self.tools = {}
        self.is_processing = False
        # Reset file tracking (but don't delete files - they stay on desktop)
        self.downloaded_files = []
        self.current_task_folder = ""


# Global state instance
api_state = APIState()

# Request/Response models
class PromptRequest(BaseModel):
    prompt: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    system_prompt_suffix: Optional[str] = None
    only_n_most_recent_images: Optional[int] = None
    webhook_url: Optional[str] = "https://example.com"
    media_ids: Optional[List[str]] = None

class PromptResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None

class StatusResponse(BaseModel):
    is_processing: bool
    messages_count: int
    last_message_role: Optional[str] = None

class ResetResponse(BaseModel):
    success: bool
    message: str

# Utility functions
def validate_auth(provider: APIProvider, api_key: str | None):
    """Validate API authentication"""
    if provider == APIProvider.ANTHROPIC:
        if not api_key:
            return "Enter your Anthropic API key to continue."
    if provider == APIProvider.BEDROCK:
        import boto3
        if not boto3.Session().get_credentials():
            return "You must have AWS credentials set up to use the Bedrock API."
    if provider == APIProvider.VERTEX:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError
        if not os.environ.get("CLOUD_ML_REGION"):
            return "Set the CLOUD_ML_REGION environment variable to use the Vertex API."
        try:
            google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except DefaultCredentialsError:
            return "Your google cloud credentials are not set up correctly."
    return None

async def download_media_files(media_ids: List[str], task_folder: str) -> List[str]:
    """Download media files using AssemblyMediaService to desktop task folder"""
    downloaded_files = []
    
    if not media_ids:
        return downloaded_files
    
    # Create task directory on desktop
    os.makedirs(task_folder, exist_ok=True)
    print(f"📁 Created task folder: {task_folder}")
    print(f"⬇️  Downloading {len(media_ids)} media files to task folder")
    
    for media_id in media_ids:
        try:
            print(f"📥 Downloading media file: {media_id}")
            file_path = download_media_from_assembly(media_id, task_folder)
            downloaded_files.append(file_path)
            print(f"✅ Successfully downloaded: {file_path}")
        except Exception as e:
            print(f"❌ Failed to download media {media_id}: {e}")
            # Continue with other files even if one fails
    
    return downloaded_files

async def send_webhook(webhook_url: str, results: Dict[str, Any]):
    """Send results to webhook URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=results,
                timeout=30.0
            )
            response.raise_for_status()
            print(f"Webhook sent successfully to {webhook_url}")
    except Exception as e:
        print(f"Failed to send webhook to {webhook_url}: {e}")

def _api_response_callback(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
):
    """Handle API response by storing it to state"""
    response_id = datetime.now().isoformat()
    api_state.responses[response_id] = (request, response)
    if error:
        print(f"API Error: {error}")

def _tool_output_callback(
    tool_output: ToolResult, tool_id: str
):
    """Handle tool output by storing it to state"""
    api_state.tools[tool_id] = tool_output

def _output_callback(content_block: BetaContentBlockParam):
    """Handle output from the sampling loop"""
    # This could be used for real-time updates if needed
    pass

async def process_prompt_async(
    prompt: str,
    webhook_url: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    system_prompt_suffix: Optional[str] = None,
    only_n_most_recent_images: Optional[int] = None,
    media_ids: Optional[List[str]] = None
):
    """Process the prompt asynchronously"""
    try:
        api_state.is_processing = True
        
        # Generate task ID for this request
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_folder = os.path.join(api_state.desktop_path, task_id)
        api_state.current_task_folder = task_folder
        print(f"🆔 Task ID: {task_id}")
        print(f"📁 Task folder: {task_folder}")
        
        # Update configuration if provided
        if api_key:
            api_state.api_key = api_key
        if model:
            api_state.model = model
        if provider:
            api_state.provider = APIProvider(provider)
        if system_prompt_suffix:
            api_state.custom_system_prompt = system_prompt_suffix
        if only_n_most_recent_images is not None:
            api_state.only_n_most_recent_images = only_n_most_recent_images

        # Validate authentication
        if auth_error := validate_auth(api_state.provider, api_state.api_key):
            raise Exception(f"Authentication error: {auth_error}")

        # Download media files if provided
        if media_ids:
            try:
                downloaded_files = await download_media_files(media_ids, task_folder)
                api_state.downloaded_files = downloaded_files
                
                # Add file information to prompt if files were downloaded
                if downloaded_files:
                    file_info = "\n\n📁 Downloaded Files Available for This Task:\n"
                    file_info += "=" * 50 + "\n"
                    for file_path in downloaded_files:
                        file_name = os.path.basename(file_path)
                        file_size = os.path.getsize(file_path)
                        file_info += f"📄 File: {file_name}\n"
                        file_info += f"   📂 Full Path: {file_path}\n"
                        file_info += f"   📊 Size: {file_size:,} bytes\n"
                        file_info += f"   🔗 Use this exact path in your tools: {file_path}\n\n"
                    
                    file_info += "💡 Instructions:\n"
                    file_info += "- Use the exact file paths shown above when working with these files\n"
                    file_info += "- You can read, edit, analyze, or upload these files as needed\n"
                    file_info += f"- Files are stored in desktop folder: {task_folder}\n"
                    file_info += "- Files will remain available after task completion\n"
                    
                    prompt = prompt + file_info
                    print(f"Enhanced prompt with detailed file information for {len(downloaded_files)} files")
            except Exception as e:
                print(f"Warning: Failed to download some media files: {e}")
                results = {
                    "success": False,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "result": "Failed to download media files",
                }
                # Continue processing even if media download fails

        # Add user message
        api_state.messages.append(
            {
                "role": Sender.USER,
                "content": [BetaTextBlockParam(type="text", text=prompt)],
            }
        )

        # Run the sampling loop
        api_state.messages = await sampling_loop(
            system_prompt_suffix=api_state.custom_system_prompt,
            model=api_state.model,
            provider=api_state.provider,
            messages=api_state.messages,
            output_callback=_output_callback,
            tool_output_callback=_tool_output_callback,
            api_response_callback=_api_response_callback,
            api_key=api_state.api_key,
            only_n_most_recent_images=api_state.only_n_most_recent_images,
        )

        # Prepare results for webhook
        results = {
            "success": True,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "steps_performed": len(api_state.messages),
            "result": None
        }

        # Get the last assistant message
        for message in reversed(api_state.messages):
            if message["role"] == "assistant":
                if isinstance(message["content"], list):
                    for block in message["content"]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            results["last_response"] = block.get("text", "")
                            break
                break

        # Send webhook
        await send_webhook(webhook_url, results)

        # Reset state for next request (no cleanup - files stay on desktop)
        api_state.reset()

    except Exception as e:
        error_results = {
            "success": False,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        # Send error webhook
        await send_webhook(webhook_url, error_results)
        
        # Reset state even on error (no cleanup - files stay on desktop)
        api_state.reset()
        
        print(f"Error processing prompt: {e}")
        raise

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Desktop Automation AI API",
        "version": "1.0.0",
        "endpoints": {
            "POST /prompt": "Send a prompt to the AI agent (supports media_ids for file downloads)",
            "GET /status": "Get current processing status",
            "POST /reset": "Reset the session state (files remain on desktop)",
            "GET /health": "Health check"
        },
        "features": {
            "media_download": "Supports downloading files via media_ids using Assembly Media Service",
            "auto_cleanup": "Downloaded files are automatically cleaned up after task completion or session reset"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current processing status"""
    last_message_role = None
    if api_state.messages:
        last_message_role = api_state.messages[-1]["role"]
    
    return StatusResponse(
        is_processing=api_state.is_processing,
        messages_count=len(api_state.messages),
        last_message_role=last_message_role
    )

@app.post("/reset", response_model=ResetResponse)
async def reset_session():
    """Reset the session state and cleanup downloaded files"""
    if api_state.is_processing:
        return ResetResponse(
            success=False,
            message="Cannot reset while processing. Please wait for current task to complete."
        )
    
    api_state.reset()
    return ResetResponse(
        success=True,
        message="Session state has been reset. Downloaded files remain available on desktop."
    )


@app.post("/prompt", response_model=PromptResponse)
async def process_prompt(request: PromptRequest, background_tasks: BackgroundTasks):
    """
    Process a prompt with the AI agent.
    The processing happens asynchronously and results are sent to the webhook URL.
    """
    if api_state.is_processing:
        raise HTTPException(
            status_code=429, 
            detail="Another request is currently being processed. Please wait."
        )
    
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt cannot be empty."
        )

    # Task ID will be generated in process_prompt_async

    # Add background task
    background_tasks.add_task(
        process_prompt_async,
        prompt=request.prompt,
        webhook_url=request.webhook_url or "https://example.com",
        api_key=request.api_key,
        model=request.model,
        provider=request.provider,
        system_prompt_suffix=request.system_prompt_suffix,
        only_n_most_recent_images=request.only_n_most_recent_images,
        media_ids=request.media_ids
    )

    return PromptResponse(
        success=True,
        message="Prompt received and is being processed. Results will be sent to webhook URL.",
        task_id=None  # Task ID will be available in webhook response
    )

if __name__ == "__main__":
    import uvicorn
    
    # Check if required environment variables are set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY environment variable not set")
    
    print("Starting Desktop Automation AI API Server...")
    print("API Documentation will be available at: http://localhost:8000/docs")
    print("Streamlit app should be running separately on port 8501")
    
    # Disable reload in production to avoid infinite reload loops
    # especially when running from a batch file or when venv changes
    reload_enabled = os.getenv("FASTAPI_RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
        reload_excludes=["venv/*", "*.log", "tmp/*", "__pycache__/*"] if reload_enabled else None,
        log_level="info"
    )