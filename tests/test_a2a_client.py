"""
Unit Tests for Agent Zero A2A Client

Tests cover:
- Basic message sending and receiving
- Context preservation across messages
- Company research functionality
- Contact discovery and enrichment
- Error handling and retries
- Timeout scenarios
- JSON parsing from various formats
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

try:
    import httpx
except ImportError:
    pytest.skip("httpx not installed", allow_module_level=True)

from core.a2a_client import (
    AgentZeroClient,
    A2AResponse,
    CompanyData,
    ContactData,
    A2AMessageRole,
)


class TestAgentZeroClient:
    """Test suite for AgentZeroClient."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv("AGENT_ZERO_URL", "http://test-agent-zero.local")
        monkeypatch.setenv("AGENT_ZERO_TOKEN", "test-token-123")

    @pytest.fixture
    def client(self, mock_env):
        """Create test client instance."""
        return AgentZeroClient(
            timeout=30,
            max_retries=2,
            retry_delay=0.1,
        )

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        mock_client = AsyncMock()
        mock_response = Mock()  # Use Mock, not AsyncMock for response
        mock_response.json = Mock(return_value={
            "response": "Test response",
            "context_id": "ctx-123",
            "metadata": {},
        })
        mock_response.raise_for_status = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        return mock_client

    def test_client_initialization(self, mock_env):
        """Test client initialization with environment variables."""
        client = AgentZeroClient()
        
        assert client.base_url == "http://test-agent-zero.local"
        assert client.token == "test-token-123"
        assert client.timeout == 300
        assert client.max_retries == 3
        assert client.a2a_endpoint == "http://test-agent-zero.local/a2a/t-test-token-123"

    def test_client_initialization_custom_params(self):
        """Test client initialization with custom parameters."""
        client = AgentZeroClient(
            base_url="http://custom.local",
            token="custom-token",
            timeout=60,
            max_retries=5,
        )
        
        assert client.base_url == "http://custom.local"
        assert client.token == "custom-token"
        assert client.timeout == 60
        assert client.max_retries == 5

    def test_client_missing_token(self, monkeypatch):
        """Test client behavior when token is missing."""
        monkeypatch.delenv("AGENT_ZERO_TOKEN", raising=False)
        
        client = AgentZeroClient()
        assert client.token is None
        
        with pytest.raises(ValueError, match="AGENT_ZERO_TOKEN not configured"):
            _ = client.a2a_endpoint

    @pytest.mark.asyncio
    async def test_send_message_basic(self, client, mock_httpx_client):
        """Test basic message sending."""
        client.client = mock_httpx_client
        
        response = await client._send_message("Hello, Agent Zero!")
        
        assert isinstance(response, A2AResponse)
        assert response.response == "Test response"
        assert response.context_id == "ctx-123"
        
        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == client.a2a_endpoint
        assert call_args[1]["json"]["message"] == "Hello, Agent Zero!"

    @pytest.mark.asyncio
    async def test_send_message_with_context(self, client, mock_httpx_client):
        """Test message sending with context preservation."""
        client.client = mock_httpx_client
        
        response1 = await client._send_message(
            "First message",
            context_key="test_context"
        )
        
        assert "test_context" in client._contexts
        assert client._contexts["test_context"] == "ctx-123"
        
        response2 = await client._send_message(
            "Second message",
            context_key="test_context"
        )
        
        second_call_args = mock_httpx_client.post.call_args_list[1]
        assert second_call_args[1]["json"]["context_id"] == "ctx-123"

    @pytest.mark.asyncio
    async def test_send_message_reset_context(self, client, mock_httpx_client):
        """Test resetting conversation context."""
        client.client = mock_httpx_client
        
        await client._send_message("First", context_key="test")
        assert "test" in client._contexts
        
        await client._send_message("Second", context_key="test", reset_context=True)
        
        first_call = mock_httpx_client.post.call_args_list[0]
        assert "context_id" not in first_call[1]["json"]

    @pytest.mark.asyncio
    async def test_send_message_with_attachments(self, client, mock_httpx_client):
        """Test sending message with attachments."""
        client.client = mock_httpx_client
        
        attachments = ["http://example.com/file.pdf", "/path/to/local/file.txt"]
        await client._send_message(
            "Message with attachments",
            attachments=attachments
        )
        
        call_args = mock_httpx_client.post.call_args
        assert call_args[1]["json"]["attachments"] == attachments

    @pytest.mark.asyncio
    async def test_send_message_retry_on_error(self, client):
        """Test retry logic on HTTP errors."""
        mock_client = AsyncMock()
        
        error_response = AsyncMock()
        error_response.raise_for_status.side_effect = httpx.HTTPError("Server error")
        
        success_response = AsyncMock()
        success_response.json.return_value = {
            "response": "Success after retry",
            "context_id": "ctx-456",
        }
        success_response.raise_for_status = Mock()
        
        mock_client.post.side_effect = [
            error_response,
            error_response,
            success_response,
        ]
        
        client.client = mock_client
        
        response = await client._send_message("Test retry")
        
        assert response.response == "Success after retry"
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_message_max_retries_exceeded(self, client):
        """Test failure after max retries exceeded."""
        mock_client = AsyncMock()
        
        error_response = AsyncMock()
        error_response.raise_for_status.side_effect = httpx.HTTPError("Server error")
        mock_client.post.return_value = error_response
        
        client.client = mock_client
        
        with pytest.raises(httpx.HTTPError):
            await client._send_message("Test max retries")
        
        assert mock_client.post.call_count == 2

    def test_parse_json_response_direct_json(self, client):
        """Test parsing direct JSON response."""
        response_text = '{"name": "Test Company", "industry": "Tech"}'
        
        data = client._parse_json_response(response_text)
        
        assert data["name"] == "Test Company"
        assert data["industry"] == "Tech"

    def test_parse_json_response_markdown_code_block(self, client):
        """Test parsing JSON from markdown code block."""
        response_text = 'Here is the data:\n```json\n{"name": "Test"}\n```'
        
        data = client._parse_json_response(response_text)
        assert data["name"] == "Test"

    def test_parse_json_response_no_json(self, client):
        """Test error when no JSON found in response."""
        response_text = "This is just plain text with no JSON."
        
        with pytest.raises(ValueError, match="No valid JSON found"):
            client._parse_json_response(response_text)

    @pytest.mark.asyncio
    async def test_research_company_success(self, client, mock_httpx_client):
        """Test successful company research."""
        company_json = {
            "name": "Acme Corp",
            "domain": "acme.com",
            "industry": "Technology",
            "size": "100-500 employees",
            "location": "San Francisco, CA",
            "description": "Leading tech company",
            "technologies": ["Python", "React", "AWS"],
            "social_media": {
                "linkedin": "https://linkedin.com/company/acme"
            },
            "key_people": [{"name": "John Doe", "role": "CEO"}],
            "recent_news": ["Acme raises $50M Series B"]
        }
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "response": json.dumps(company_json),
            "context_id": "ctx-company-123",
        }
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response
        
        client.client = mock_httpx_client
        
        result = await client.research_company("Acme Corp", "acme.com")
        
        assert isinstance(result, CompanyData)
        assert result.name == "Acme Corp"
        assert result.domain == "acme.com"
        assert result.industry == "Technology"
        assert len(result.technologies) == 3

    @pytest.mark.asyncio
    async def test_find_contacts_success(self, client, mock_httpx_client):
        """Test successful contact discovery."""
        contacts_json = [
            {
                "name": "Dr. John Smith",
                "email": "john@acme.com",
                "role": "Chief Medical Officer",
                "company": "Acme Medical"
            }
        ]
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "response": json.dumps(contacts_json),
            "context_id": "ctx-contacts-123",
        }
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response
        
        client.client = mock_httpx_client
        
        result = await client.find_contacts("Acme Medical", roles=["doctor"])
        
        assert len(result) == 1
        assert result[0].name == "Dr. John Smith"

    @pytest.mark.asyncio
    async def test_enrich_contact_success(self, client, mock_httpx_client):
        """Test successful contact enrichment."""
        contact_json = {
            "name": "John Doe",
            "email": "john@acme.com",
            "role": "Senior Engineer",
            "interests": ["AI", "Python"]
        }
        
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "response": json.dumps(contact_json),
            "context_id": "ctx-enrich-123",
        }
        mock_response.raise_for_status = Mock()
        mock_httpx_client.post.return_value = mock_response
        
        client.client = mock_httpx_client
        
        result = await client.enrich_contact(email="john@acme.com")
        
        assert isinstance(result, ContactData)
        assert result.name == "John Doe"
        assert len(result.interests) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
