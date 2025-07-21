import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests
import boto3
from botocore.exceptions import ClientError


class MediaUploadResponse:
    """Response model for media upload."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data.get('id', '')
        self.name: str = data.get('name', '')
        self.thumbnail: str = data.get('thumbnail', '')
        self.media: str = data.get('media', '')
        self.size_mb: float = data.get('sizeMB', 0.0)
        self.upload_complete: bool = data.get('uploadComplete', False)
        self.description: str = data.get('description', '')
        self.owners: List[str] = data.get('owners', [])


class MediaDownloadResponse:
    """Response model for media download."""
    
    def __init__(self, data: Dict[str, Any]):
        self.url: str = data.get('url', '')


class AssemblyMediaService:
    """
    Python implementation of the AssemblyMediaService for handling media uploads and downloads.
    Mirrors the functionality of the TypeScript version in browser-interface.
    """
    
    _instance: Optional['AssemblyMediaService'] = None
    
    def __init__(self):
        self.base_url = os.getenv(
            'ASSEMBLY_BASE_URL', 
            'https://orch-api-dev.assembly-industries.com'
        )
        self._secret_key: Optional[str] = None
    
    @classmethod
    def get_instance(cls) -> 'AssemblyMediaService':
        """Get singleton instance of AssemblyMediaService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _get_secret_key(self) -> str:
        """
        Retrieve the secret key from AWS Secrets Manager.
        
        Returns:
            str: The secret key for API authentication
            
        Raises:
            Exception: If unable to retrieve the secret key
        """
        if self._secret_key:
            return self._secret_key
        
        secret_name = os.getenv('ASSEMBLY_SECRET_NAME')
        region = os.getenv('AWS_SSM_REGION')
        
        if not secret_name or not region:
            raise Exception("ASSEMBLY_SECRET_NAME and AWS_SSM_REGION environment variables must be set")
        
        # Create a Secrets Manager client
        client = boto3.client(
            'secretsmanager',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' not in response:
                raise Exception("Secret string is empty")
            
            secret_data = json.loads(response['SecretString'])
            self._secret_key = secret_data.get('secretKey')
            
            if not self._secret_key:
                raise Exception("service_secret_key not found in secret")
            
            return self._secret_key
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve secret key: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse secret JSON")
        except Exception as e:
            raise Exception(f"Failed to retrieve secret key: {str(e)}")
    
    def _get_secret_key_sync(self) -> str:
        """
        Synchronous version of _get_secret_key for easier use.
        
        Returns:
            str: The secret key for API authentication
        """
        if self._secret_key:
            return self._secret_key
        
        secret_name = os.getenv('ASSEMBLY_SECRET_NAME')
        region = os.getenv('AWS_SSM_REGION')
        
        if not secret_name or not region:
            raise Exception("ASSEMBLY_SECRET_NAME and AWS_SSM_REGION environment variables must be set")
        
        # Create a Secrets Manager client
        client = boto3.client(
            'secretsmanager',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' not in response:
                raise Exception("Secret string is empty")
            
            secret_data = json.loads(response['SecretString'])
            self._secret_key = secret_data.get('secretKey')
            
            if not self._secret_key:
                raise Exception("service_secret_key not found in secret")
            
            return self._secret_key
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve secret key: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse secret JSON")
        except Exception as e:
            raise Exception(f"Failed to retrieve secret key: {str(e)}")
    
    def upload_media(
        self, 
        file_path: str, 
        description: Optional[str] = None
    ) -> MediaUploadResponse:
        """
        Upload a media file to Assembly.
        
        Args:
            file_path (str): Path to the file to upload
            description (str, optional): Description for the media file
            
        Returns:
            MediaUploadResponse: Response containing upload details
            
        Raises:
            Exception: If upload fails
        """
        secret_key = self._get_secret_key_sync()
        
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        file_name = os.path.basename(file_path)
        
        # Prepare the multipart form data
        files = {
            'file': (file_name, open(file_path, 'rb'), 'application/octet-stream')
        }
        
        data = {}
        if description:
            data['description'] = description
        
        headers = {
            'Authorization': f'Bearer {secret_key}'
        }
        
        try:
            response = requests.put(
                f"{self.base_url}/v0/media/services/browser-interface/media",
                headers=headers,
                files=files,
                data=data
            )
            
            # Close the file
            files['file'][1].close()
            
            if not response.ok:
                error_text = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_text)
                except:
                    error_message = error_text
                
                raise Exception(f"Media upload failed ({response.status_code}): {error_message}")
            
            response_data = response.json()
            return MediaUploadResponse(response_data)
            
        except requests.RequestException as e:
            raise Exception(f"Media upload failed: {str(e)}")
        except Exception as e:
            raise e
    
    def upload_media_from_bytes(
        self, 
        file_buffer: bytes, 
        file_name: str, 
        description: Optional[str] = None
    ) -> MediaUploadResponse:
        """
        Upload a media file from a bytes buffer to Assembly.
        
        Args:
            file_buffer (bytes): File data as bytes
            file_name (str): Name for the file
            description (str, optional): Description for the media file
            
        Returns:
            MediaUploadResponse: Response containing upload details
            
        Raises:
            Exception: If upload fails
        """
        secret_key = self._get_secret_key_sync()
        
        # Prepare the multipart form data
        files = {
            'file': (file_name, file_buffer, 'application/octet-stream')
        }
        
        data = {}
        if description:
            data['description'] = description
        
        headers = {
            'Authorization': f'Bearer {secret_key}'
        }
        
        try:
            response = requests.put(
                f"{self.base_url}/v0/media/services/browser-interface/media",
                headers=headers,
                files=files,
                data=data
            )
            
            if not response.ok:
                error_text = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_text)
                except:
                    error_message = error_text
                
                raise Exception(f"Media upload failed ({response.status_code}): {error_message}")
            
            response_data = response.json()
            return MediaUploadResponse(response_data)
            
        except requests.RequestException as e:
            raise Exception(f"Media upload failed: {str(e)}")
        except Exception as e:
            raise e

    def upload_media_buffer(
        self, 
        file_path: str, 
        description: Optional[str] = None
    ) -> MediaUploadResponse:
        """
        Upload a media file from an absolute file path to Assembly.
        
        Args:
            file_path (str): Absolute path to the file to upload
            description (str, optional): Description for the media file
            
        Returns:
            MediaUploadResponse: Response containing upload details
            
        Raises:
            Exception: If upload fails or file not found
        """
        secret_key = self._get_secret_key_sync()
        
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        file_name = os.path.basename(file_path)
        
        # Read file and prepare the multipart form data
        with open(file_path, 'rb') as file:
            file_buffer = file.read()
        
        files = {
            'file': (file_name, file_buffer, 'application/octet-stream')
        }
        
        data = {}
        if description:
            data['description'] = description
        
        headers = {
            'Authorization': f'Bearer {secret_key}'
        }
        
        try:
            response = requests.put(
                f"{self.base_url}/v0/media/services/browser-interface/media",
                headers=headers,
                files=files,
                data=data
            )
            
            if not response.ok:
                error_text = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_text)
                except:
                    error_message = error_text
                
                raise Exception(f"Media upload failed ({response.status_code}): {error_message}")
            
            response_data = response.json()
            return MediaUploadResponse(response_data)
            
        except requests.RequestException as e:
            raise Exception(f"Media upload failed: {str(e)}")
        except Exception as e:
            raise e
    
    def get_media_download_url(self, media_id: str) -> str:
        """
        Get the download URL for a media file.
        
        Args:
            media_id (str): ID of the media file
            
        Returns:
            str: Download URL for the media file
            
        Raises:
            Exception: If unable to get download URL
        """
        secret_key = self._get_secret_key_sync()
        
        headers = {
            'Authorization': f'Bearer {secret_key}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v0/media/services/conversation/browser-interface/media/{media_id}",
                headers=headers
            )
            
            if not response.ok:
                error_text = response.text
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_text)
                except:
                    error_message = error_text
                
                raise Exception(f"Failed to get download URL ({response.status_code}): {error_message}")
            
            response_data = response.json()
            download_response = MediaDownloadResponse(response_data)
            return download_response.url
            
        except requests.RequestException as e:
            raise Exception(f"Failed to get download URL: {str(e)}")
        except Exception as e:
            raise e
    
    def download_media_for_desktop(
        self, 
        media_id: str, 
        download_dir: str = "./tmp", 
        max_retries: int = 3
    ) -> str:
        """
        Download a media file to the local filesystem.
        
        Args:
            media_id (str): ID of the media file to download
            download_dir (str): Directory to save the downloaded file
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            str: Path to the downloaded file
            
        Raises:
            Exception: If download fails after all retries
        """
        for attempt in range(1, max_retries + 1):
            try:
                download_url = self.get_media_download_url(media_id)
                
                # Extract filename from the URL
                url_parts = download_url.split("/")
                last_part = url_parts[-1]
                filename = last_part.split("?")[0]  # Remove query parameters
                
                # Create download directory if it doesn't exist
                Path(download_dir).mkdir(parents=True, exist_ok=True)
                
                # Use the extracted filename in download directory
                file_path = os.path.join(download_dir, filename)
                
                response = requests.get(download_url, stream=True)
                
                if not response.ok:
                    if response.status_code == 403 and attempt < max_retries:
                        print(f"Download URL expired, retrying... (attempt {attempt + 1})")
                        time.sleep(1)  # Wait before retry
                        continue
                    
                    raise Exception(f"Download failed with status: {response.status_code}")
                
                # Write the file
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"Media downloaded successfully to: {file_path}")
                return file_path
                
            except Exception as e:
                if attempt >= max_retries:
                    raise e
                print(f"Download attempt {attempt} failed, retrying...")
                time.sleep(1)
        
        raise Exception(f"Failed to download media after {max_retries} attempts")


# Convenience functions for easier usage
def upload_media_to_assembly(file_path: str, description: Optional[str] = None) -> MediaUploadResponse:
    """
    Convenience function to upload a media file to Assembly.
    
    Args:
        file_path (str): Path to the file to upload
        description (str, optional): Description for the media file
        
    Returns:
        MediaUploadResponse: Response containing upload details
    """
    service = AssemblyMediaService.get_instance()
    return service.upload_media(file_path, description)


def upload_media_buffer_to_assembly(
    file_path: str, 
    description: Optional[str] = None
) -> MediaUploadResponse:
    """
    Convenience function to upload a media file from absolute path to Assembly.
    
    Args:
        file_path (str): Absolute path to the file to upload
        description (str, optional): Description for the media file
        
    Returns:
        MediaUploadResponse: Response containing upload details
    """
    service = AssemblyMediaService.get_instance()
    return service.upload_media_buffer(file_path, description)


def upload_media_bytes_to_assembly(
    file_buffer: bytes, 
    file_name: str, 
    description: Optional[str] = None
) -> MediaUploadResponse:
    """
    Convenience function to upload a media buffer (bytes) to Assembly.
    
    Args:
        file_buffer (bytes): File data as bytes
        file_name (str): Name for the file
        description (str, optional): Description for the media file
        
    Returns:
        MediaUploadResponse: Response containing upload details
    """
    service = AssemblyMediaService.get_instance()
    return service.upload_media_from_bytes(file_buffer, file_name, description)


def download_media_from_assembly(
    media_id: str, 
    download_dir: str = "./tmp"
) -> str:
    """
    Convenience function to download a media file from Assembly.
    
    Args:
        media_id (str): ID of the media file to download
        download_dir (str): Directory to save the downloaded file
        
    Returns:
        str: Path to the downloaded file
    """
    service = AssemblyMediaService.get_instance()
    return service.download_media_for_desktop(media_id, download_dir)


def get_media_download_url_from_assembly(media_id: str) -> str:
    """
    Convenience function to get a media download URL from Assembly.
    
    Args:
        media_id (str): ID of the media file
        
    Returns:
        str: Download URL for the media file
    """
    service = AssemblyMediaService.get_instance()
    return service.get_media_download_url(media_id) 