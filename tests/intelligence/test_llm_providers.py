"""Tests for LLM provider implementations."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import os

pytestmark = pytest.mark.asyncio


class TestLLMProviderInterface:
    """Tests for LLM provider interface compliance."""
    
    def test_provider_must_implement_complete(self):
        """Test that providers must implement complete method."""
        from blackcore.intelligence.interfaces import ILLMProvider
        
        # Verify abstract method exists
        assert hasattr(ILLMProvider, 'complete')
        
        # Verify it's abstract
        with pytest.raises(TypeError):
            # Should not be able to instantiate abstract class
            ILLMProvider()
    
    def test_provider_must_implement_complete_with_functions(self):
        """Test that providers must implement complete_with_functions method."""
        from blackcore.intelligence.interfaces import ILLMProvider
        
        assert hasattr(ILLMProvider, 'complete_with_functions')
    
    def test_provider_must_implement_estimate_tokens(self):
        """Test that providers must implement estimate_tokens method."""
        from blackcore.intelligence.interfaces import ILLMProvider
        
        assert hasattr(ILLMProvider, 'estimate_tokens')


class TestClaudeProvider:
    """Tests for Claude LLM provider."""
    
    @pytest.fixture
    def mock_anthropic(self):
        """Mock anthropic client."""
        with patch('blackcore.intelligence.llm.providers.anthropic') as mock:
            mock_client = AsyncMock()
            mock.AsyncAnthropic.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    async def claude_provider(self, mock_anthropic):
        """Create Claude provider instance."""
        from blackcore.intelligence.llm.providers import ClaudeProvider
        return ClaudeProvider(api_key="test-key", model="claude-3-opus-20240229")
    
    async def test_claude_initialization(self):
        """Test Claude provider initialization."""
        from blackcore.intelligence.llm.providers import ClaudeProvider
        
        # Test with explicit API key
        provider = ClaudeProvider(api_key="test-key", model="claude-3-opus")
        assert provider.api_key == "test-key"
        assert provider.model == "claude-3-opus"
        
        # Test with environment variable
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            provider = ClaudeProvider()
            assert provider.api_key == "env-key"
            assert provider.model == "claude-3-opus-20240229"  # default
    
    async def test_claude_complete(self, claude_provider, mock_anthropic):
        """Test Claude completion."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_anthropic.messages.create = AsyncMock(return_value=mock_response)
        
        # Test completion
        result = await claude_provider.complete(
            prompt="Test prompt",
            system_prompt="You are a test assistant",
            temperature=0.5,
            max_tokens=100
        )
        
        assert result == "Test response"
        
        # Verify API call
        mock_anthropic.messages.create.assert_called_once()
        call_args = mock_anthropic.messages.create.call_args
        assert call_args.kwargs['model'] == "claude-3-opus-20240229"
        assert call_args.kwargs['temperature'] == 0.5
        assert call_args.kwargs['max_tokens'] == 100
        
        # Check messages format
        messages = call_args.kwargs['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'You are a test assistant'
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == 'Test prompt'
    
    async def test_claude_complete_json_mode(self, claude_provider, mock_anthropic):
        """Test Claude completion with JSON response format."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"result": "test"}')]
        mock_anthropic.messages.create = AsyncMock(return_value=mock_response)
        
        result = await claude_provider.complete(
            prompt="Generate data",
            response_format={"type": "json_object"}
        )
        
        # Verify JSON instruction added
        call_args = mock_anthropic.messages.create.call_args
        messages = call_args.kwargs['messages']
        assert "Respond with valid JSON only." in messages[-1]['content']
    
    async def test_claude_complete_with_functions(self, claude_provider, mock_anthropic):
        """Test Claude function calling simulation."""
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps({
            "function": "get_weather",
            "arguments": {"location": "New York"}
        }))]
        mock_anthropic.messages.create = AsyncMock(return_value=mock_response)
        
        functions = [{
            "name": "get_weather",
            "description": "Get weather for location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }]
        
        result = await claude_provider.complete_with_functions(
            prompt="What's the weather in New York?",
            functions=functions
        )
        
        assert result["function"] == "get_weather"
        assert result["arguments"]["location"] == "New York"
    
    def test_claude_estimate_tokens(self, claude_provider):
        """Test Claude token estimation."""
        # Test various text lengths
        assert claude_provider.estimate_tokens("") == 0
        assert claude_provider.estimate_tokens("Hello world") > 0
        assert claude_provider.estimate_tokens("A" * 1000) > 200
        
        # Test that longer text has more tokens
        short_tokens = claude_provider.estimate_tokens("Short text")
        long_tokens = claude_provider.estimate_tokens("This is a much longer text " * 10)
        assert long_tokens > short_tokens


class TestOpenAIProvider:
    """Tests for OpenAI LLM provider."""
    
    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client."""
        with patch('blackcore.intelligence.llm.providers.openai') as mock:
            mock_client = AsyncMock()
            mock.AsyncOpenAI.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    async def openai_provider(self, mock_openai):
        """Create OpenAI provider instance."""
        from blackcore.intelligence.llm.providers import OpenAIProvider
        return OpenAIProvider(api_key="test-key", model="gpt-4")
    
    async def test_openai_initialization(self):
        """Test OpenAI provider initialization."""
        from blackcore.intelligence.llm.providers import OpenAIProvider
        
        # Test with explicit API key
        provider = OpenAIProvider(api_key="test-key", model="gpt-4-turbo")
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4-turbo"
        
        # Test with environment variable
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            provider = OpenAIProvider()
            assert provider.api_key == "env-key"
            assert provider.model == "gpt-4"  # default
    
    async def test_openai_complete(self, openai_provider, mock_openai):
        """Test OpenAI completion."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await openai_provider.complete(
            prompt="Test prompt",
            system_prompt="You are a test assistant",
            temperature=0.7,
            max_tokens=150
        )
        
        assert result == "Test response"
        
        # Verify API call
        mock_openai.chat.completions.create.assert_called_once()
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args.kwargs['model'] == "gpt-4"
        assert call_args.kwargs['temperature'] == 0.7
        assert call_args.kwargs['max_tokens'] == 150
    
    async def test_openai_complete_json_mode(self, openai_provider, mock_openai):
        """Test OpenAI completion with JSON response format."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"result": "test"}'))]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await openai_provider.complete(
            prompt="Generate data",
            response_format={"type": "json_object"}
        )
        
        # Verify response_format passed to API
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args.kwargs['response_format'] == {"type": "json_object"}
    
    async def test_openai_complete_with_functions(self, openai_provider, mock_openai):
        """Test OpenAI native function calling."""
        # Setup mock response with function call
        mock_response = Mock()
        mock_response.choices = [Mock(
            message=Mock(
                function_call=Mock(
                    name="get_weather",
                    arguments='{"location": "New York"}'
                )
            )
        )]
        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
        
        functions = [{
            "name": "get_weather",
            "description": "Get weather for location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }]
        
        result = await openai_provider.complete_with_functions(
            prompt="What's the weather in New York?",
            functions=functions
        )
        
        assert result["function"] == "get_weather"
        assert result["arguments"]["location"] == "New York"
        
        # Verify functions passed to API
        call_args = mock_openai.chat.completions.create.call_args
        assert call_args.kwargs['functions'] == functions
    
    def test_openai_estimate_tokens(self, openai_provider):
        """Test OpenAI token estimation with tiktoken."""
        # Should use tiktoken for accurate counting
        tokens = openai_provider.estimate_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10  # Should be around 4 tokens
        
        # Test empty string
        assert openai_provider.estimate_tokens("") == 0


class TestLiteLLMProvider:
    """Tests for LiteLLM provider."""
    
    @pytest.fixture
    def mock_litellm(self):
        """Mock litellm module."""
        with patch('blackcore.intelligence.llm.providers.acompletion') as mock_acomp:
            yield mock_acomp
    
    @pytest.fixture
    async def litellm_provider(self):
        """Create LiteLLM provider instance."""
        from blackcore.intelligence.llm.providers import LiteLLMProvider
        return LiteLLMProvider(model="gpt-3.5-turbo", api_base="http://localhost:8000")
    
    async def test_litellm_initialization(self):
        """Test LiteLLM provider initialization."""
        from blackcore.intelligence.llm.providers import LiteLLMProvider
        
        provider = LiteLLMProvider(
            model="claude-2",
            api_key="test-key",
            api_base="https://api.example.com"
        )
        assert provider.model == "claude-2"
        assert provider.api_key == "test-key"
        assert provider.api_base == "https://api.example.com"
    
    async def test_litellm_complete(self, litellm_provider, mock_litellm):
        """Test LiteLLM completion."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_litellm.return_value = mock_response
        
        result = await litellm_provider.complete(
            prompt="Test prompt",
            system_prompt="System prompt",
            temperature=0.8
        )
        
        assert result == "Test response"
        
        # Verify litellm call
        mock_litellm.assert_called_once()
        call_args = mock_litellm.call_args
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"
        assert call_args.kwargs['temperature'] == 0.8
        assert call_args.kwargs['api_base'] == "http://localhost:8000"
    
    async def test_litellm_router_support(self):
        """Test LiteLLM router configuration support."""
        from blackcore.intelligence.llm.providers import LiteLLMProvider
        
        # Test router model syntax
        provider = LiteLLMProvider(model="router/gpt-4-load-balanced")
        assert provider.model == "router/gpt-4-load-balanced"
        
        # Test with custom headers
        provider = LiteLLMProvider(
            model="custom/llm-endpoint",
            extra_headers={"X-API-Key": "custom-key"}
        )
        assert provider.extra_headers["X-API-Key"] == "custom-key"
    
    def test_litellm_estimate_tokens(self, litellm_provider):
        """Test LiteLLM token estimation fallback."""
        # Should fall back to approximation
        tokens = litellm_provider.estimate_tokens("Hello, world!")
        assert tokens > 0
        assert tokens == len("Hello, world!") // 4  # Default approximation


class TestProviderSelection:
    """Tests for provider selection and configuration."""
    
    async def test_provider_factory(self):
        """Test creating providers through factory."""
        from blackcore.intelligence.llm.factory import create_llm_provider
        
        # Test Claude provider
        claude = create_llm_provider("claude", api_key="test-key")
        assert claude.__class__.__name__ == "ClaudeProvider"
        
        # Test OpenAI provider
        openai = create_llm_provider("openai", api_key="test-key")
        assert openai.__class__.__name__ == "OpenAIProvider"
        
        # Test LiteLLM provider
        litellm = create_llm_provider("litellm", model="gpt-3.5-turbo")
        assert litellm.__class__.__name__ == "LiteLLMProvider"
        
        # Test invalid provider
        with pytest.raises(ValueError):
            create_llm_provider("invalid-provider")


class TestProviderErrorHandling:
    """Tests for provider error handling."""
    
    @pytest.fixture
    async def failing_provider(self):
        """Create a provider that fails."""
        from blackcore.intelligence.llm.providers import ClaudeProvider
        provider = ClaudeProvider(api_key="test-key")
        # Mock to raise exception
        provider.client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        return provider
    
    async def test_completion_error_handling(self, failing_provider):
        """Test error handling in completion."""
        with pytest.raises(Exception) as exc_info:
            await failing_provider.complete("Test prompt")
        assert "API Error" in str(exc_info.value)
    
    async def test_retry_logic(self):
        """Test retry logic for transient errors."""
        from blackcore.intelligence.llm.providers import ClaudeProvider
        
        provider = ClaudeProvider(api_key="test-key")
        
        # Mock to fail twice then succeed
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return Mock(content=[Mock(text="Success")])
        
        provider.client.messages.create = mock_create
        
        # Should succeed after retries
        result = await provider.complete("Test", max_retries=3)
        assert result == "Success"
        assert call_count == 3