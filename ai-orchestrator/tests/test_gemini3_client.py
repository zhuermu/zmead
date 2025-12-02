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


class TestAgents:
    """Test sub-agents."""

    @pytest.fixture
    def mock_gemini_client(self):
        """Mock Gemini client for agents."""
        with patch("app.agents.creative.get_gemini3_client") as mock:
            client = AsyncMock()
            client.generate_image = AsyncMock(return_value=b"fake_image")
            client.generate_video = AsyncMock(return_value={"operation_id": "op123"})
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_gcs_client(self):
        """Mock GCS client."""
        with patch("app.agents.creative.get_gcs_client") as mock:
            client = AsyncMock()
            client.upload_for_chat_display = AsyncMock(return_value={
                "gcs_url": "gs://bucket/image.png",
                "public_url": "https://storage.googleapis.com/bucket/image.png",
                "object_name": "image.png",
            })
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_credit_client(self):
        """Mock credit client."""
        with patch("app.agents.creative.get_credit_client") as mock:
            client = AsyncMock()
            client.check_credit = AsyncMock(return_value=True)
            client.deduct_credit = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_temp_storage(self):
        """Mock temp storage."""
        with patch("app.agents.creative.store_temp_creative") as mock_store, \
             patch("app.agents.creative.store_temp_batch") as mock_batch:
            mock_store.return_value = "temp_123"
            mock_batch.return_value = "batch_456"
            yield mock_store, mock_batch

    @pytest.mark.asyncio
    async def test_creative_agent_generate_image(
        self,
        mock_gemini_client,
        mock_gcs_client,
        mock_credit_client,
        mock_temp_storage,
    ):
        """Test creative agent image generation."""
        from app.agents.creative import CreativeAgent
        from app.agents.base import AgentContext

        agent = CreativeAgent()
        agent.gemini_client = mock_gemini_client

        context = AgentContext(
            user_id="test_user",
            session_id="test_session",
        )

        result = await agent.execute(
            action="generate_image",
            params={
                "prompt": "Test product",
                "count": 2,
                "style": "现代风格",
            },
            context=context,
        )

        assert result.success
        assert "creatives" in result.data
        assert len(result.data["creatives"]) == 2

    @pytest.mark.asyncio
    async def test_performance_agent_get_report(self):
        """Test performance agent report generation."""
        from app.agents.performance import PerformanceAgent
        from app.agents.base import AgentContext

        agent = PerformanceAgent()

        context = AgentContext(
            user_id="test_user",
            session_id="test_session",
        )

        result = await agent.execute(
            action="get_report",
            params={
                "platform": "meta",
                "date_range": "last_7_days",
            },
            context=context,
        )

        assert result.success
        assert "summary" in result.data
        assert "campaigns" in result.data

    @pytest.mark.asyncio
    async def test_performance_agent_detect_anomalies(self):
        """Test performance agent anomaly detection."""
        from app.agents.performance import PerformanceAgent
        from app.agents.base import AgentContext

        agent = PerformanceAgent()

        context = AgentContext(
            user_id="test_user",
            session_id="test_session",
        )

        result = await agent.execute(
            action="detect_anomalies",
            params={
                "metrics": ["roas", "cpa"],
                "sensitivity": "medium",
            },
            context=context,
        )

        assert result.success
        assert "anomalies" in result.data

    @pytest.mark.asyncio
    async def test_campaign_agent_create_campaign(self):
        """Test campaign agent campaign creation."""
        from app.agents.campaign import CampaignAgent
        from app.agents.base import AgentContext

        agent = CampaignAgent()

        context = AgentContext(
            user_id="test_user",
            session_id="test_session",
        )

        result = await agent.execute(
            action="create_campaign",
            params={
                "platform": "meta",
                "budget": 100,
                "target_roas": 3.0,
            },
            context=context,
        )

        assert result.success
        assert "campaign_id" in result.data


class TestOrchestrator:
    """Test main orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator initializes agents."""
        from app.core.orchestrator import Orchestrator
        from app.agents.registry import get_agent_registry

        with patch("app.core.orchestrator.get_gemini3_client"):
            orchestrator = Orchestrator()
            orchestrator._ensure_initialized()

            registry = get_agent_registry()
            assert len(registry) >= 5  # At least 5 agents registered

    @pytest.mark.asyncio
    async def test_orchestrator_process_message_mocked(self):
        """Test orchestrator message processing with mocked Gemini."""
        from app.core.orchestrator import Orchestrator

        with patch("app.core.orchestrator.get_gemini3_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat_with_tools = AsyncMock(return_value={
                "response": "Test response",
                "messages": [],
                "iterations": 1,
            })
            mock_get_client.return_value = mock_client

            orchestrator = Orchestrator()
            result = await orchestrator.process_message(
                user_id="test_user",
                session_id="test_session",
                message="Hello",
            )

            assert result["success"]
            assert result["response"] == "Test response"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
