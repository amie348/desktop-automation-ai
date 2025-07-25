"""Upload tool for handling document uploads when users request to upload documents or when files are present."""

import os
from typing import Literal

from anthropic.types.beta import BetaToolUnionParam

from .base import BaseAnthropicTool, ToolResult
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.assembly_media_service import (
    AssemblyMediaService, 
    upload_media_buffer_to_assembly,
    MediaUploadResponse
)


class UploadTool(BaseAnthropicTool):
    """
    An upload tool that handles document uploads when users request to upload documents or when files are present.
    Integrates with AssemblyMediaService for actual file uploads.
    """

    api_type: Literal["custom"] = "custom"
    name: Literal["upload_tool"] = "upload_tool"
    
    def __init__(self):
        super().__init__()
        self.media_service = AssemblyMediaService.get_instance()
        # Track uploaded files for this session
        self.uploaded_files = []

    def to_params(self) -> BetaToolUnionParam:
        return {
            "name": self.name,
            "type": self.api_type,
            "description": "Upload documents when user requests to upload files which are present in the local machine or when files are present. Handles document upload to configured endpoint.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["upload_file", "list_uploads", "get_upload_status", "get_media_url"],
                        "description": "The upload action to perform"
                    },
                    "file_path": {
                        "type": "string", 
                        "description": "Local path of the file to upload (required for upload_file action)"
                    },
                    "upload_name": {
                        "type": "string",
                        "description": "Name to use for the uploaded file (optional, defaults to original filename)"
                    },
                    "file_type": {
                        "type": "string",
                        "description": "Type of file being uploaded (pdf, docx, txt, jpg, etc.)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata to include with the upload (optional)"
                    },
                    "media_id": {
                        "type": "string",
                        "description": "Media ID for getting download URL (required for get_media_url action)"
                    }
                },
                "required": ["action"]
            }
        }

    async def __call__(
        self,
        *,
        action: str,
        file_path: str | None = None,
        upload_name: str | None = None, 
        file_type: str | None = None,
        metadata: dict | None = None,
        media_id: str | None = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute the upload tool with the given parameters.
        Currently using print statements as placeholders for actual implementation.
        """
        
        try:
            if action == "upload_file":
                if not file_path:
                    return ToolResult(
                        error="file_path is required for upload_file action"
                    )
                
                print(f"[UPLOAD TOOL] Starting upload process...")
                print(f"[UPLOAD TOOL] File path: {file_path}")
                print(f"[UPLOAD TOOL] File type: {file_type}")
                print(f"[UPLOAD TOOL] Upload name: {upload_name or 'original filename'}")
                
                # Check if file exists
                if not os.path.exists(file_path):
                    return ToolResult(
                        error=f"File not found: {file_path}"
                    )
                
                # Get file info
                file_size = os.path.getsize(file_path)
                file_size_mb = file_size / (1024 * 1024)
                
                print(f"[UPLOAD TOOL] File size: {file_size_mb:.2f} MB")
                
                # Prepare description with metadata
                description = f"Uploaded via desktop automation"
                if metadata:
                    description += f" - Metadata: {metadata}"
                if upload_name:
                    description += f" - Custom name: {upload_name}"
                if file_type:
                    description += f" - Type: {file_type}"
                
                try:
                    # Actually upload the file using AssemblyMediaService
                    print(f"[UPLOAD TOOL] Uploading to Assembly Media Service...")
                    upload_response = upload_media_buffer_to_assembly(file_path, description)
                    
                    # Track the uploaded file
                    upload_info = {
                        'id': upload_response.id,
                        'name': upload_response.name,
                        'original_path': file_path,
                        'size_mb': upload_response.size_mb,
                        'thumbnail': upload_response.thumbnail,
                        'media_url': upload_response.media,
                        'upload_complete': upload_response.upload_complete
                    }
                    self.uploaded_files.append(upload_info)
                    
                    print(f"[UPLOAD TOOL] Upload completed successfully!")
                    print(f"[UPLOAD TOOL] Media ID: {upload_response.id}")
                    print(f"[UPLOAD TOOL] Media URL: {upload_response.media}")
                    
                    return ToolResult(
                        output=f"""File uploaded successfully!
                        
Upload Details:
- File: {file_path}
- Media ID: {upload_response.id}
- Name: {upload_response.name}
- Size: {upload_response.size_mb:.2f} MB
- Media URL: {upload_response.media}
- Thumbnail: {upload_response.thumbnail}
- Upload Complete: {upload_response.upload_complete}
- Description: {description}"""
                    )
                    
                except Exception as upload_error:
                    error_msg = f"Upload failed: {str(upload_error)}"
                    print(f"[UPLOAD TOOL] Error: {error_msg}")
                    return ToolResult(error=error_msg)
                
            elif action == "list_uploads":
                print(f"[UPLOAD TOOL] Listing uploads from this session...")
                
                if not self.uploaded_files:
                    print(f"[UPLOAD TOOL] No files uploaded in this session")
                    return ToolResult(
                        output="No files uploaded in this session"
                    )
                
                print(f"[UPLOAD TOOL] Found {len(self.uploaded_files)} uploaded files:")
                
                upload_list = []
                for i, upload in enumerate(self.uploaded_files, 1):
                    file_info = f"- {upload['name']} (ID: {upload['id']}, Size: {upload['size_mb']:.2f} MB)"
                    print(f"[UPLOAD TOOL] {file_info}")
                    upload_list.append(file_info)
                
                return ToolResult(
                    output=f"Uploaded files in this session ({len(self.uploaded_files)} total):\n" + 
                           "\n".join(upload_list)
                )
                
            elif action == "get_upload_status":
                print(f"[UPLOAD TOOL] Checking upload status...")
                
                completed_uploads = len([f for f in self.uploaded_files if f['upload_complete']])
                incomplete_uploads = len([f for f in self.uploaded_files if not f['upload_complete']])
                total_uploads = len(self.uploaded_files)
                
                total_size_mb = sum(f['size_mb'] for f in self.uploaded_files)
                
                print(f"[UPLOAD TOOL] Total uploads: {total_uploads}")
                print(f"[UPLOAD TOOL] Completed uploads: {completed_uploads}")
                print(f"[UPLOAD TOOL] Incomplete uploads: {incomplete_uploads}")
                print(f"[UPLOAD TOOL] Total size uploaded: {total_size_mb:.2f} MB")
                print(f"[UPLOAD TOOL] Assembly Media Service endpoint")
                
                return ToolResult(
                    output=f"""Upload Status Summary:
- Total uploads: {total_uploads}
- Completed uploads: {completed_uploads}
- Incomplete uploads: {incomplete_uploads}
- Total size uploaded: {total_size_mb:.2f} MB
- Service: Assembly Media Service"""
                )
                
            elif action == "get_media_url":
                if not media_id:
                    return ToolResult(
                        error="media_id is required for get_media_url action"
                    )
                
                print(f"[UPLOAD TOOL] Getting download URL for media ID: {media_id}")
                
                try:
                    download_url = self.media_service.get_media_download_url(media_id)
                    
                    # Check if this media_id is from our uploaded files
                    uploaded_file = next((f for f in self.uploaded_files if f['id'] == media_id), None)
                    
                    if uploaded_file:
                        print(f"[UPLOAD TOOL] Found in session uploads: {uploaded_file['name']}")
                        return ToolResult(
                            output=f"""Media Download URL Retrieved:
- Media ID: {media_id}
- File Name: {uploaded_file['name']}
- Download URL: {download_url}
- Original Path: {uploaded_file['original_path']}
- Size: {uploaded_file['size_mb']:.2f} MB"""
                        )
                    else:
                        print(f"[UPLOAD TOOL] Media ID not from this session")
                        return ToolResult(
                            output=f"""Media Download URL Retrieved:
- Media ID: {media_id}
- Download URL: {download_url}
- Note: This media was not uploaded in this session"""
                        )
                        
                except Exception as e:
                    error_msg = f"Failed to get download URL: {str(e)}"
                    print(f"[UPLOAD TOOL] Error: {error_msg}")
                    return ToolResult(error=error_msg)
                
            else:
                print(f"[UPLOAD TOOL] Error: Unknown action '{action}'")
                return ToolResult(
                    error=f"Unknown action: {action}. Supported actions: upload_file, list_uploads, get_upload_status, get_media_url"
                )
                
        except Exception as e:
            print(f"[UPLOAD TOOL] Error occurred: {str(e)}")
            return ToolResult(
                error=f"Upload tool error: {str(e)}"
            )