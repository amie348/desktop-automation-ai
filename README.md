# Anthropic Computer Use Demo - Windows Version

I created this because the version Anthropic released is plainly not useful for understanding what Agents can do; it is limited to a Linux Vm run in docker. You need to actually use this thing with your daily driver to understand the potential! Be careful, you absolutely can cause real damage to your system if you aren't responsible with this. You set an intelligence loose in your system, you take upon yourself certain risks. But...also some great rewards! --Christopher


> [!CAUTION]
> Computer use is a beta feature. Please be aware that computer use poses unique risks that are distinct from standard API features or chat interfaces. These risks are heightened when using computer use to interact with the internet. To minimize risks, consider taking precautions such as:
>
> 1. Use a dedicated virtual machine or container with minimal privileges to prevent direct system attacks or accidents.
> 2. Avoid giving the model access to sensitive data, such as account login information, to prevent information theft.
> 3. Limit internet access to an allowlist of domains to reduce exposure to malicious content.
> 4. Ask a human to confirm decisions that may result in meaningful real-world consequences as well as any tasks requiring affirmative consent, such as accepting cookies, executing financial transactions, or agreeing to terms of service.
>
> In some circumstances, Claude will follow commands found in content even if it conflicts with the user's instructions. For example, instructions on webpages or contained in images may override user instructions or cause Claude to make mistakes. We suggest taking precautions to isolate Claude from sensitive data and actions to avoid risks related to prompt injection.
>
> Finally, please inform end users of relevant risks and obtain their consent prior to enabling computer use in your own products.

This repository provides a Windows-compatible version of the Anthropic Computer Use demo, implementing:

* A computer use agent loop using the Anthropic API, Bedrock, or Vertex to access the updated Claude 3.5 Sonnet model
* Anthropic-defined computer use tools adapted for Windows
* A streamlit app for interacting with the agent loop

This thing can get Very Expensive! Please set your API limits responsibly --Christopher

> [!IMPORTANT]
> The Beta API used in this reference implementation is subject to change. Please refer to the [API release notes](https://docs.anthropic.com/en/release-notes/api) for the most up-to-date information.

## Prerequisites

- Windows 10 or later
- Python 3.7-3.12 (3.13 is currently not supported by some dependencies)
- Administrator privileges may be required for installing Python packages

## Installation

1. Clone this repository:


2. Run the setup script:
```cmd
setup.bat
```

This will:
- Create a Python virtual environment
- Install required dependencies
- Set up pre-commit hooks

## Configuration

### Anthropic API

> [!TIP]
> You can find your API key in the [Anthropic Console](https://console.anthropic.com/).

Set your Anthropic API key as an environment variable:

If using Command Prompt (cmd.exe):
```cmd
set ANTHROPIC_API_KEY=your_api_key
```

If using PowerShell:
```powershell
$env:ANTHROPIC_API_KEY = "your_api_key"
```

### Bedrock

> [!TIP]
> To use the new Claude 3.5 Sonnet on Bedrock, you first need to [request model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html).

You'll need to set up AWS credentials with appropriate permissions to use Claude on Bedrock.

Set the following environment variables:

If using Command Prompt (cmd.exe):
```cmd
set API_PROVIDER=bedrock
set AWS_PROFILE=your_aws_profile
set AWS_REGION=us-west-2
```

If using PowerShell:
```powershell
$env:API_PROVIDER = "bedrock"
$env:AWS_PROFILE = "your_aws_profile"
$env:AWS_REGION = "us-west-2"
```

Alternatively, you can use access keys:

If using Command Prompt (cmd.exe):
```cmd
set API_PROVIDER=bedrock
set AWS_ACCESS_KEY_ID=your_aws_access_key
set AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
set AWS_SESSION_TOKEN=your_aws_session_token
set AWS_REGION=us-west-2
```

If using PowerShell:
```powershell
$env:API_PROVIDER = "bedrock"
$env:AWS_ACCESS_KEY_ID = "your_aws_access_key"
$env:AWS_SECRET_ACCESS_KEY = "your_aws_secret_access_key"
$env:AWS_SESSION_TOKEN = "your_aws_session_token"
$env:AWS_REGION = "us-west-2"
```

### Vertex

Set up Google Cloud credentials with appropriate permissions and set the following environment variables:

If using Command Prompt (cmd.exe):
```cmd
set API_PROVIDER=vertex
set CLOUD_ML_REGION=your_vertex_region
set ANTHROPIC_VERTEX_PROJECT_ID=your_vertex_project_id
set GOOGLE_APPLICATION_CREDENTIALS=path_to_your_credentials.json
```

If using PowerShell:
```powershell
$env:API_PROVIDER = "vertex"
$env:CLOUD_ML_REGION = "your_vertex_region"
$env:ANTHROPIC_VERTEX_PROJECT_ID = "your_vertex_project_id"
$env:GOOGLE_APPLICATION_CREDENTIALS = "path_to_your_credentials.json"
```

## Running the Demo

1. Activate the virtual environment:

If using Command Prompt (cmd.exe):
```cmd
.venv\Scripts\activate.bat
```

If using PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

Note: If you get a PowerShell execution policy error, you may need to run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. Start the Streamlit app:
```cmd
python -m streamlit run computer_use_demo\streamlit.py
```

3. Open your browser to [http://localhost:8501](http://localhost:8501) to access the interface.

## Screen Resolution

You can configure the screen resolution using environment variables:

If using Command Prompt (cmd.exe):
```cmd
set WIDTH=1920
set HEIGHT=1080
```

If using PowerShell:
```powershell
$env:WIDTH = "1920"
$env:HEIGHT = "1080"
```

We do not recommend sending screenshots in resolutions above [XGA/WXGA](https://en.wikipedia.org/wiki/Display_resolution_standards#XGA) to avoid issues related to [image resizing](https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size).

The Windows implementation automatically scales both images and coordinates from higher resolutions to the suggested resolutions for optimal performance.

## Assembly Media Service

The desktop automation AI now includes a complete Python implementation of the AssemblyMediaService, mirroring the functionality from the browser-interface TypeScript version.

### Features

- **Media Upload**: Upload files or buffers to Assembly with authentication
- **Media Download**: Download media files with retry logic and URL expiration handling  
- **AWS Integration**: Secure credential management via AWS Secrets Manager
- **Singleton Pattern**: Efficient resource management with single instance
- **Error Handling**: Comprehensive error handling and retry mechanisms

### Setup

1. **Environment Variables**: Set the following environment variables:
   ```bash
   ASSEMBLY_BASE_URL=https://orch-api-dev.assembly-industries.com
   ASSEMBLY_SECRET_NAME=your-secret-name
   AWS_SSM_REGION=your-aws-region
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   ```

2. **Dependencies**: Install required packages:
   ```bash
   pip install boto3 requests
   ```

### Usage Examples

#### Basic Upload
```python
from utils import upload_media_to_assembly

# Upload a file
response = upload_media_to_assembly(
    file_path="./screenshot.png",
    description="Desktop automation screenshot"
)
print(f"Media ID: {response.id}")
print(f"Media URL: {response.media}")
```

#### Upload from Absolute Path (Buffer Function)
```python
from utils import upload_media_buffer_to_assembly

# Upload from absolute file path
response = upload_media_buffer_to_assembly(
    file_path="/full/path/to/automation_result.jpg",
    description="AI automation result"
)
```

#### Upload from Bytes Buffer
```python
from utils import upload_media_bytes_to_assembly

# Upload from bytes buffer
with open("image.jpg", "rb") as f:
    buffer_data = f.read()

response = upload_media_bytes_to_assembly(
    file_buffer=buffer_data,
    file_name="automation_result.jpg",
    description="AI automation result"
)
```

#### Download Media
```python
from utils import download_media_from_assembly

# Download a media file
local_path = download_media_from_assembly(
    media_id="media_123456",
    download_dir="./downloads"
)
print(f"Downloaded to: {local_path}")
```

#### Using the Service Class Directly
```python
from utils import AssemblyMediaService

# Get singleton instance
service = AssemblyMediaService.get_instance()

# Upload with more control
response = service.upload_media(
    file_path="./data.csv",
    description="Extracted data from automation"
)

# Get download URL
download_url = service.get_media_download_url(response.id)
```

### Integration with Data Extraction Tools

The AssemblyMediaService works seamlessly with the data extraction tools to upload screenshots and extracted data:

```python
# Example: Upload screenshot after data extraction
from tools.data_extraction import DataExtractionTool
from utils import upload_media_to_assembly

# Extract data (this takes a screenshot)
extraction_tool = DataExtractionTool()
result = await extraction_tool(
    extraction_type="table",
    extraction_instructions="Extract product data"
)

# Upload the screenshot to Assembly for storage
if result.base64_image:
    # Convert base64 to file and upload
    import base64
    image_data = base64.b64decode(result.base64_image)
    
    # Save temporarily
    temp_path = "./tmp/extraction_screenshot.png"
    with open(temp_path, "wb") as f:
        f.write(image_data)
    
    # Upload to Assembly
    upload_response = upload_media_to_assembly(
        file_path=temp_path,
        description="Data extraction screenshot"
    )
    
    print(f"Screenshot uploaded: {upload_response.id}")
```

### Error Handling

The service includes comprehensive error handling:

```python
try:
    response = upload_media_to_assembly("./file.pdf")
    print(f"Upload successful: {response.id}")
except Exception as e:
    print(f"Upload failed: {e}")
```

### File Organization

- `utils/assembly_media_service.py` - Main service implementation
- `utils/__init__.py` - Package initialization and exports

## Development

1. Install development dependencies:
```cmd
pip install -r dev-requirements.txt
```

2. Run tests:
```cmd
python -m pytest tests
```

## Troubleshooting

1. If you encounter permission errors when installing packages, try running the command prompt as Administrator.

2. If the mouse or keyboard control doesn't work:
   - Ensure you're not running any software that blocks PyAutoGUI
   - Try running the application as Administrator
   - Check that your antivirus software isn't blocking the automation

3. If screenshots are not working:
   - Ensure you have the latest version of Pillow installed
   - Try updating your graphics drivers

  
If you're having any issues or questions, email me at chris@christopherdanielbradford.com. Have fun!
