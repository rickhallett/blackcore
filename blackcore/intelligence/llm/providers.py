"""LLM provider implementations."""

import os
import json
from typing import Dict, List, Any, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

try:
    from litellm import acompletion, completion
except ImportError:
    acompletion = None
    completion = None

from ..interfaces import ILLMProvider


class ClaudeProvider(ILLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Add JSON mode instruction if needed
        if response_format and response_format.get("type") == "json_object":
            messages[-1]["content"] += "\n\nRespond with valid JSON only."
        
        # Handle retries
        max_retries = getattr(self, 'max_retries', 0)
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 4000
                )
                return response.content[0].text
            except Exception as e:
                if attempt == max_retries:
                    raise
                # Continue to next retry
        
        return ""  # Should never reach here
    
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        # Claude doesn't have native function calling yet
        # We'll simulate it with prompting
        functions_desc = json.dumps(functions, indent=2)
        
        enhanced_prompt = f"""You have access to the following functions:
{functions_desc}

To use a function, respond with a JSON object in this format:
{{
    "function": "function_name",
    "arguments": {{...}}
}}

User request: {prompt}"""
        
        response = await self.complete(
            enhanced_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"function": None, "arguments": {}}
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for Claude."""
        # Claude uses a similar tokenizer to GPT models
        # Approximate: 1 token ≈ 4 characters
        return len(text) // 4 if text else 0


class OpenAIProvider(ILLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        
        # Initialize tiktoken encoder
        if tiktoken:
            try:
                self.encoder = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fallback to cl100k_base for newer models
                self.encoder = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoder = None
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        if response_format:
            kwargs["response_format"] = response_format
        
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            functions=functions,
            temperature=temperature
        )
        
        # Extract function call
        message = response.choices[0].message
        if hasattr(message, 'function_call') and message.function_call:
            return {
                "function": message.function_call.name,
                "arguments": json.loads(message.function_call.arguments)
            }
        
        return {"function": None, "arguments": {}}
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken."""
        if not text:
            return 0
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Fallback approximation
            return len(text) // 4


class LiteLLMProvider(ILLMProvider):
    """LiteLLM unified provider."""
    
    def __init__(
        self, 
        model: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.extra_headers = extra_headers or {}
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers
        
        response = await acompletion(**kwargs)
        return response.choices[0].message.content
    
    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        # LiteLLM handles function calling based on the underlying model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "functions": functions,
            "temperature": temperature
        }
        
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        response = await acompletion(**kwargs)
        
        # Extract function call
        message = response.choices[0].message
        if hasattr(message, 'function_call') and message.function_call:
            return {
                "function": message.function_call.name,
                "arguments": json.loads(message.function_call.arguments)
            }
        
        return {"function": None, "arguments": {}}
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (fallback approximation)."""
        # LiteLLM doesn't provide token counting
        # Use character-based approximation
        return len(text) // 4 if text else 0