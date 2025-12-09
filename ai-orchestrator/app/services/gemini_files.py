"""Gemini Files API utilities for file upload and management."""

import logging
import os
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Gemini Files API base URL
GEMINI_FILES_API_BASE = "https://generativelanguage.googleapis.com"

# Global flag to track if Gemini is available
_gemini_available: bool | None = None

# GCS client singleton
_gcs_client = None


def get_gcs_client():
    """Get GCS client instance (lazy initialization)."""
    global _gcs_client

    if _gcs_client is not None:
        return _gcs_client

    try:
        from google.cloud import storage

        if settings.gcs_credentials_path:
            _gcs_client = storage.Client.from_service_account_json(settings.gcs_credentials_path)
        elif settings.gcs_project_id:
            _gcs_client = storage.Client(project=settings.gcs_project_id)
        else:
            # Try default credentials
            _gcs_client = storage.Client()

        logger.info("GCS client initialized successfully")
        return _gcs_client
    except Exception as e:
        logger.warning(f"GCS client initialization failed: {e}")
        return None


@lru_cache(maxsize=1)
def get_gemini_client():
    """Get Gemini client instance (lazy initialization).

    Returns None if API key is not available.
    """
    global _gemini_available

    try:
        import google.generativeai as genai

        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured. Gemini file upload will be disabled.")
            _gemini_available = False
            return None

        genai.configure(api_key=settings.gemini_api_key)
        _gemini_available = True
        return genai
    except Exception as e:
        logger.warning(f"Gemini client initialization failed: {e}. Gemini features will be disabled.")
        _gemini_available = False
        return None


def is_gemini_available() -> bool:
    """Check if Gemini is available."""
    if _gemini_available is None:
        get_gemini_client()  # Trigger lazy initialization
    return _gemini_available or False


class GeminiFilesService:
    """Gemini Files API service for uploading files to Gemini."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = get_gemini_client()
        return self._client

    def _check_available(self) -> bool:
        """Check if Gemini is available."""
        if not is_gemini_available():
            logger.warning("Gemini operation skipped: API not available")
            return False
        return True

    def download_from_url(self, url: str, timeout: float = 30.0) -> bytes | None:
        """
        Download file from HTTP/HTTPS URL (e.g., signed GCS URL).

        Args:
            url: HTTP/HTTPS URL to download from
            timeout: Request timeout in seconds (default 30s)

        Returns:
            File content as bytes, or None if download fails
        """
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()

                data = response.content
                logger.info(f"Downloaded {len(data)} bytes from URL: {url[:100]}...")
                return data

        except httpx.TimeoutException:
            logger.error(f"Timeout downloading from URL: {url[:100]}...")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading from URL: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to download from URL: {e}")
            return None

    def upload_from_url(
        self,
        url: str,
        mime_type: str,
        display_name: str | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any] | None:
        """
        Download file from URL and upload to Gemini Files API.

        Args:
            url: HTTP/HTTPS URL to download from (e.g., signed GCS URL)
            mime_type: MIME type of the file
            display_name: Optional display name for the file
            timeout: Download timeout in seconds

        Returns:
            Dictionary with Gemini file info or None if upload fails
        """
        # Download from URL
        data = self.download_from_url(url, timeout)
        if not data:
            return None

        # Upload to Gemini
        return self.upload_file(data, mime_type, display_name)

    def download_from_gcs(self, gcs_uri: str) -> bytes | None:
        """
        Download file from GCS.

        Args:
            gcs_uri: GCS URI in format gs://bucket/path/to/file

        Returns:
            File content as bytes, or None if download fails
        """
        try:
            # Parse GCS URI
            if not gcs_uri.startswith("gs://"):
                logger.error(f"Invalid GCS URI: {gcs_uri}")
                return None

            uri_parts = gcs_uri[5:].split("/", 1)
            if len(uri_parts) != 2:
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return None

            bucket_name, blob_path = uri_parts

            # Get GCS client
            gcs_client = get_gcs_client()
            if not gcs_client:
                logger.error("GCS client not available")
                return None

            # Download file
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                logger.error(f"GCS file not found: {gcs_uri}")
                return None

            data = blob.download_as_bytes()
            logger.info(f"Downloaded {len(data)} bytes from GCS: {gcs_uri}")
            return data

        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            return None

    def upload_from_gcs(
        self,
        gcs_uri: str,
        mime_type: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Download file from GCS and upload to Gemini Files API.

        Args:
            gcs_uri: GCS URI in format gs://bucket/path/to/file
            mime_type: MIME type of the file
            display_name: Optional display name for the file

        Returns:
            Dictionary with Gemini file info or None if upload fails
        """
        # Download from GCS
        data = self.download_from_gcs(gcs_uri)
        if not data:
            return None

        # Upload to Gemini
        return self.upload_file(data, mime_type, display_name)

    def _get_http_client(self, timeout: float = 60.0) -> httpx.Client:
        """Get HTTP client with optional proxy support.

        Args:
            timeout: Request timeout in seconds

        Returns:
            httpx.Client configured with proxy if environment variable is set
        """
        # Check for proxy at runtime (not module load time)
        proxy_url = os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY")

        if proxy_url and proxy_url.startswith("socks5://"):
            # Use httpx-socks for SOCKS5 proxy
            try:
                from httpx_socks import SyncProxyTransport
                transport = SyncProxyTransport.from_url(proxy_url)
                logger.info(f"Using SOCKS5 proxy: {proxy_url}")
                return httpx.Client(transport=transport, timeout=timeout)
            except ImportError:
                logger.warning("httpx-socks not installed, proxy will not be used")
                return httpx.Client(timeout=timeout)
        elif proxy_url:
            # Use standard HTTP/HTTPS proxy
            logger.info(f"Using HTTP proxy: {proxy_url}")
            return httpx.Client(timeout=timeout, proxy=proxy_url)
        else:
            # No proxy
            return httpx.Client(timeout=timeout)

    def _upload_file_via_curl(
        self,
        data: bytes,
        mime_type: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Upload file to Gemini using curl (fallback for SSL issues with Python).

        Uses curl subprocess which handles SSL better with SOCKS5 proxies.

        Args:
            data: File content as bytes
            mime_type: MIME type of the file
            display_name: Optional display name for the file

        Returns:
            Dictionary with file info or None if upload fails
        """
        import json
        import subprocess
        import tempfile

        proxy_url = os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY")
        logger.info(f"Uploading file to Gemini via curl, size={len(data)}, mime={mime_type}, proxy={proxy_url}")

        # Write data to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_extension(mime_type)) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name

        try:
            # Step 1: Initiate resumable upload
            init_url = f"{GEMINI_FILES_API_BASE}/upload/v1beta/files?key={settings.gemini_api_key}"
            metadata = json.dumps({"file": {"displayName": display_name or "uploaded_file"}})

            curl_cmd = ["curl", "-s", "-D", "-"]
            if proxy_url:
                if proxy_url.startswith("socks5://"):
                    curl_cmd.extend(["--socks5", proxy_url.replace("socks5://", "")])
                else:
                    curl_cmd.extend(["--proxy", proxy_url])

            curl_cmd.extend([
                "-X", "POST",
                "-H", "X-Goog-Upload-Protocol: resumable",
                "-H", "X-Goog-Upload-Command: start",
                "-H", f"X-Goog-Upload-Header-Content-Length: {len(data)}",
                "-H", f"X-Goog-Upload-Header-Content-Type: {mime_type}",
                "-H", "Content-Type: application/json",
                "-d", metadata,
                init_url,
            ])

            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"curl init failed: {result.stderr}")
                return None

            # Parse headers to get upload URL
            output = result.stdout
            upload_url = None
            for line in output.split("\n"):
                if line.lower().startswith("x-goog-upload-url:"):
                    upload_url = line.split(":", 1)[1].strip()
                    break

            if not upload_url:
                logger.error(f"No upload URL in curl response: {output[:500]}")
                return None

            logger.info(f"Got upload URL via curl, uploading {len(data)} bytes...")

            # Step 2: Upload file content
            curl_cmd2 = ["curl", "-s"]
            if proxy_url:
                if proxy_url.startswith("socks5://"):
                    curl_cmd2.extend(["--socks5", proxy_url.replace("socks5://", "")])
                else:
                    curl_cmd2.extend(["--proxy", proxy_url])

            curl_cmd2.extend([
                "-X", "POST",
                "-H", "X-Goog-Upload-Command: upload, finalize",
                "-H", "X-Goog-Upload-Offset: 0",
                "-H", f"Content-Type: {mime_type}",
                "--data-binary", f"@{tmp_path}",
                upload_url,
            ])

            result2 = subprocess.run(curl_cmd2, capture_output=True, text=True, timeout=120)

            if result2.returncode != 0:
                logger.error(f"curl upload failed: {result2.stderr}")
                return None

            # Parse JSON response
            try:
                response_data = json.loads(result2.stdout)
                file_info = response_data.get("file", {})

                logger.info(f"File uploaded to Gemini via curl: {file_info.get('name')}")

                return {
                    "name": file_info.get("name", ""),
                    "uri": file_info.get("uri", ""),
                    "display_name": file_info.get("displayName", display_name or ""),
                    "mime_type": file_info.get("mimeType", mime_type),
                    "size_bytes": file_info.get("sizeBytes", len(data)),
                    "state": file_info.get("state", "ACTIVE"),
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse curl response: {result2.stdout[:500]}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("curl upload timed out")
            return None
        except Exception as e:
            logger.error(f"curl upload failed: {e}")
            return None
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def upload_file(
        self,
        data: bytes,
        mime_type: str,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Upload file to Gemini Files API.

        First tries Python httpx client, falls back to curl if SSL errors occur.

        Args:
            data: File content as bytes
            mime_type: MIME type of the file
            display_name: Optional display name for the file

        Returns:
            Dictionary with file info including:
            - name: The Gemini file name (used as URI in prompts)
            - uri: The file URI for use in prompts
            - display_name: Display name
            - mime_type: MIME type
            - size_bytes: File size
            Returns None if upload fails or Gemini is not available
        """
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not available")
            return None

        proxy_url = os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY")

        # Try Python httpx first
        try:
            logger.info(f"Uploading file to Gemini via httpx, size={len(data)}, mime={mime_type}, proxy={proxy_url}")

            # Step 1: Initiate resumable upload
            init_url = f"{GEMINI_FILES_API_BASE}/upload/v1beta/files?key={settings.gemini_api_key}"

            metadata = {"file": {"displayName": display_name or "uploaded_file"}}

            with self._get_http_client(timeout=120.0) as client:
                # Initial request to get upload URI
                init_response = client.post(
                    init_url,
                    headers={
                        "X-Goog-Upload-Protocol": "resumable",
                        "X-Goog-Upload-Command": "start",
                        "X-Goog-Upload-Header-Content-Length": str(len(data)),
                        "X-Goog-Upload-Header-Content-Type": mime_type,
                        "Content-Type": "application/json",
                    },
                    json=metadata,
                )

                if init_response.status_code != 200:
                    logger.error(f"Failed to initiate upload: {init_response.status_code} - {init_response.text[:500]}")
                    return None

                # Get upload URI from response headers
                upload_url = init_response.headers.get("X-Goog-Upload-URL")
                if not upload_url:
                    logger.error("No upload URL in response headers")
                    return None

                logger.info(f"Got upload URL, uploading {len(data)} bytes...")

                # Step 2: Upload file content
                upload_response = client.post(
                    upload_url,
                    headers={
                        "X-Goog-Upload-Command": "upload, finalize",
                        "X-Goog-Upload-Offset": "0",
                        "Content-Type": mime_type,
                    },
                    content=data,
                )

                if upload_response.status_code != 200:
                    logger.error(f"Failed to upload file: {upload_response.status_code} - {upload_response.text[:500]}")
                    return None

                result = upload_response.json()
                file_info = result.get("file", {})

                logger.info(f"File uploaded to Gemini via httpx: {file_info.get('name')}")

                return {
                    "name": file_info.get("name", ""),
                    "uri": file_info.get("uri", ""),
                    "display_name": file_info.get("displayName", display_name or ""),
                    "mime_type": file_info.get("mimeType", mime_type),
                    "size_bytes": file_info.get("sizeBytes", len(data)),
                    "state": file_info.get("state", "ACTIVE"),
                }

        except httpx.TimeoutException:
            logger.error("Timeout uploading file to Gemini via httpx")
            # Fall through to curl fallback
        except Exception as e:
            error_str = str(e)
            if "SSL" in error_str or "EOF" in error_str:
                logger.warning(f"SSL error with httpx, falling back to curl: {e}")
                # Fall through to curl fallback
            else:
                logger.error(f"Failed to upload file to Gemini via httpx: {e}")
                return None

        # Fallback to curl (handles SSL better with proxies)
        logger.info("Falling back to curl for Gemini upload")
        return self._upload_file_via_curl(data, mime_type, display_name)

    def _get_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "text/html": ".html",
            "application/json": ".json",
        }
        return mime_to_ext.get(mime_type, "")

    def delete_file(self, file_name: str) -> bool:
        """
        Delete file from Gemini Files API.

        Args:
            file_name: The Gemini file name (from upload response)

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self._check_available():
            return False

        try:
            self.client.delete_file(name=file_name)
            logger.info(f"File deleted from Gemini: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Gemini: {e}")
            return False

    def get_file(self, file_name: str) -> dict[str, Any] | None:
        """
        Get file metadata from Gemini Files API.

        Args:
            file_name: The Gemini file name

        Returns:
            Dictionary with file info or None if not found
        """
        if not self._check_available():
            return None

        try:
            file_info = self.client.get_file(name=file_name)
            return {
                "name": file_info.name,
                "uri": file_info.uri,
                "display_name": file_info.display_name,
                "mime_type": file_info.mime_type,
                "size_bytes": file_info.size_bytes,
                "state": file_info.state.name if hasattr(file_info, 'state') else "ACTIVE",
            }
        except Exception as e:
            logger.error(f"Failed to get file from Gemini: {e}")
            return None


# Singleton instance
gemini_files_service = GeminiFilesService()
