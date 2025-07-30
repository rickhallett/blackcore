"""Factory for creating LLM providers."""

from typing import Optional, Dict, Any
from ..interfaces import ILLMProvider
from .providers import ClaudeProvider, OpenAIProvider, LiteLLMProvider


def create_llm_provider(
    provider_type: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ILLMProvider:
    """Create an LLM provider instance.
    
    Args:
        provider_type: Type of provider ('claude', 'openai', 'litellm')
        api_key: Optional API key
        model: Optional model name
        **kwargs: Additional provider-specific arguments
        
    Returns:
        ILLMProvider instance
        
    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = provider_type.lower()
    
    if provider_type == "claude":
        return ClaudeProvider(
            api_key=api_key,
            model=model or "claude-3-opus-20240229",
            **kwargs
        )
    elif provider_type == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4",
            **kwargs
        )
    elif provider_type == "litellm":
        if not model:
            raise ValueError("Model must be specified for LiteLLM provider")
        return LiteLLMProvider(
            model=model,
            api_key=api_key,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")