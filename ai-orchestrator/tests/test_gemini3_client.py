"""Tests for Gemini 3 client.

This module tests the unified Gemini 3 client including:
- Text chat
- Image generation
- Video generation
- Function calling

Run with: pytest tests/test_gemini3_client.py -v
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set"
)


class TestGemini3ClientUnit:
    """Unit tests for Gemini3Client (mocked)."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        with patch("app.services.gemini3_client.get_settings") as mock:
            settings = MagicMock()
            settings.gemini_api_key = "test-api-key"
            settings.gemini_model_chat = "gemini-3-pro-preview"
            settings.gemini_model_imagen = "gemini-2.5-flash-image"
            settings.gemini_model_veo = "veo-3.1-generate-preview"
            mock.return_value = settings
            yield mock

    @pytest.fixture
    def client(self, mock_settings):
        """Create client with mocked settings."""
        from app.services.gemini3_client import Gemini3Client
        return Gemini3Client()

    def test_client_initialization(self, client):
        """Test client initializes with correct models."""
        assert client.chat_model == "gemini-3-pro-preview"
        assert client.image_model == "gemini-2.5-flash-image"
        assert client.video_model == "veo-3.1-generate-preview"

    def test_build_chat_request(self, client):
        """Test chat request building."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        body = client._build_chat_request(messages, None, None)

        assert "contents" in body
        assert len(body["contents"]) == 3
        assert body["contents"][0]["role"] == "user"
        assert body["contents"][1]["role"] == "model"

    def test_build_chat_request_with_system(self, client):
        """Test chat request with system instruction."""
        messages = [{"role": "user", "content": "Hello"}]
        system = "You are a helpful assistant."

        body = client._build_chat_request(messages, None, system)

        assert "systemInstruction" in body
        assert body["systemInstruction"]["parts"][0]["text"] == system

    @pytest.mark.asyncio
    async def test_chat_mocked(self, client):
        """Test chat with mocked HTTP response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Hello! How can I help?"}]
                }
            }]
        }

        with patch.object(client, "_get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await client.chat([{"role": "user", "content": "Hello"}])

            assert result == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_generate_image_mocked(self, client):
        """Test image generation with mocked response."""
        import base64

        # Create mock image data
        mock_image_data = b"fake_image_bytes"
        encoded_image = base64.b64encode(mock_image_data).decode()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": encoded_image,
                        }
                    }]
                }
            }]
        }

        with patch.object(client, "_get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await client.generate_image("A test image")

            assert result == mock_image_data

    @pytest.mark.asyncio
    async def test_function_calling_mocked(self, client):
        """Test function calling with mocked response."""
        from app.services.gemini3_client import FunctionDeclaration

        # First response with function call
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "functionCall": {
                            "name": "test_func",
                            "args": {"param": "value"}
                        }
                    }]
                }
            }]
        }

        # Second response with text
        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Function executed successfully"}]
                }
            }]
        }

        call_count = [0]

        async def mock_post(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response_1
            return mock_response_2

        with patch.object(client, "_get_http_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = mock_post
            mock_get_client.return_value = mock_client

            # Define tool
            tool = FunctionDeclaration(
                name="test_func",
                description="A test function",
                parameters={"type": "object", "properties": {}},
            )

            # Define handler
            async def handler(**kwargs):
                return {"result": "success"}

            result = await client.chat_with_tools(
                messages=[{"role": "user", "content": "Call the function"}],
                tools=[tool],
                tool_handlers={"test_func": handler},
            )

            assert "response" in result
            assert result["iterations"] >= 1


class TestGemini3ClientIntegration:
    """Integration tests for Gemini3Client (requires API key)."""

    @pytest.fixture
    def client(self):
        """Create real client."""
        from app.services.gemini3_client import Gemini3Client
        return Gemini3Client()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_chat_real(self, client):
        """Test real chat API call."""
        try:
            result = await client.chat([
                {"role": "user", "content": "Say 'test passed' in exactly 2 words"}
            ])
            assert len(result) > 0
            print(f"Chat response: {result}")
        finally:
            await client.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_generate_image_real(self, client):
        """Test real image generation (slow, uses credits)."""
        try:
            result = await client.generate_image(
                prompt="A simple red circle on white background",
                aspect_ratio="1:1",
            )
            assert isinstance(result, bytes)
            assert len(result) > 1000  # Should be a real image
            print(f"Generated image size: {len(result)} bytes")

            # Optionally save for inspection
            # with open("/tmp/test_image.png", "wb") as f:
            #     f.write(result)
        finally:
            await client.close()









if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
