# Desktop Automation AI - API Usage Guide

This document describes how to use the FastAPI server to interact with the Desktop Automation AI programmatically.

## Quick Start

### 1. Start the Servers

Run the batch file to start both Streamlit and FastAPI servers:

```bash
start_servers.bat
```

This will start:
- **Streamlit UI**: http://localhost:8501 (for interactive use)
- **FastAPI Server**: http://localhost:8000 (for programmatic access)
- **API Documentation**: http://localhost:8000/docs (interactive API docs)

### 2. Set Environment Variables

Make sure you have your Anthropic API key set:

```bash
set ANTHROPIC_API_KEY=your_api_key_here
```

Or create a `.env` file in the project directory:

```
ANTHROPIC_API_KEY=your_api_key_here
```

## API Endpoints

### POST /prompt

Send a prompt to the AI agent for processing.

**Request Body:**
```json
{
  "prompt": "Take a screenshot and tell me what you see",
  "api_key": "optional_api_key_override",
  "model": "claude-4-sonnet-20250514",
  "provider": "anthropic",
  "system_prompt_suffix": "Additional system instructions",
  "only_n_most_recent_images": 10,
  "webhook_url": "https://your-webhook-endpoint.com/results"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Prompt received and is being processed. Results will be sent to webhook URL.",
  "task_id": "task_20241201_143022"
}
```

### GET /status

Check the current processing status.

**Response:**
```json
{
  "is_processing": false,
  "messages_count": 4,
  "last_message_role": "assistant"
}
```

### POST /reset

Reset the session state (clear messages, images, etc.).

**Response:**
```json
{
  "success": true,
  "message": "Session state has been reset successfully."
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-01T14:30:22.123456"
}
```

## Webhook Response Format

After processing is complete, the API will send a POST request to your webhook URL with the results:

**Success Response:**
```json
{
  "success": true,
  "prompt": "Take a screenshot and tell me what you see",
  "timestamp": "2024-12-01T14:30:22.123456",
  "messages_count": 6,
  "last_response": "I can see a Windows desktop with..."
}
```

**Error Response:**
```json
{
  "success": false,
  "prompt": "Invalid prompt",
  "timestamp": "2024-12-01T14:30:22.123456",
  "error": "Authentication error: Enter your Anthropic API key to continue.",
  "traceback": "Traceback (most recent call last)..."
}
```

## Usage Examples

### Python Example

```python
import requests
import time

# Send a prompt
response = requests.post("http://localhost:8000/prompt", json={
    "prompt": "Take a screenshot and describe what you see on the screen",
    "webhook_url": "https://your-webhook-endpoint.com/results"
})

print(f"Task started: {response.json()}")

# Check status
status = requests.get("http://localhost:8000/status")
print(f"Status: {status.json()}")

# Reset session when done
reset_response = requests.post("http://localhost:8000/reset")
print(f"Reset: {reset_response.json()}")
```

### cURL Example

```bash
# Send a prompt
curl -X POST "http://localhost:8000/prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Open notepad and type Hello World",
    "webhook_url": "https://webhook.site/your-unique-url"
  }'

# Check status
curl "http://localhost:8000/status"

# Reset session
curl -X POST "http://localhost:8000/reset"
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function sendPrompt() {
  try {
    // Send prompt
    const response = await axios.post('http://localhost:8000/prompt', {
      prompt: 'Take a screenshot and tell me what applications are open',
      webhook_url: 'https://your-webhook-endpoint.com/results'
    });
    
    console.log('Task started:', response.data);
    
    // Poll status
    const checkStatus = async () => {
      const status = await axios.get('http://localhost:8000/status');
      console.log('Status:', status.data);
      
      if (status.data.is_processing) {
        setTimeout(checkStatus, 5000); // Check again in 5 seconds
      }
    };
    
    checkStatus();
    
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

sendPrompt();
```

## Important Notes

1. **Asynchronous Processing**: The API processes prompts asynchronously. You'll get an immediate response confirming the task has started, and results are sent to your webhook URL when complete.

2. **Single Request Limitation**: Only one prompt can be processed at a time. If you send a new request while one is processing, you'll get a 429 error.

3. **Webhook Requirement**: Results are always sent to the webhook URL after processing. Make sure your webhook endpoint can handle POST requests.

4. **State Management**: The API maintains conversation state between requests. Use the `/reset` endpoint to start fresh.

5. **Error Handling**: Errors are sent to the webhook URL with detailed information including stack traces.

6. **Security**: Be careful with API keys. You can pass them in the request body or set them as environment variables.

## Testing Your Webhook

You can use services like:
- **webhook.site** - Get a temporary webhook URL for testing
- **ngrok** - Expose your local server for webhook testing
- **requestbin.com** - Capture and inspect webhook requests

## Troubleshooting

### Common Issues

1. **"Authentication error"**: Make sure your ANTHROPIC_API_KEY is set correctly.

2. **"Another request is currently being processed"**: Wait for the current task to finish or call `/reset` to clear the state.

3. **Connection errors**: Make sure both servers are running and accessible.

4. **Webhook not received**: Check your webhook URL is accessible and can handle POST requests.

### Logs

Check the console output of the FastAPI server for detailed logs and error messages.