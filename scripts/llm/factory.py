import os
from .base import LLMProvider
from .openai_provider import OpenAIProvider

def get_llm_provider() -> LLMProvider:
    """
    Factory function that reads the .env configuration and returns the instantiated LLMProvider.
    """
    provider_name = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    elif provider_name == "gemini":
        # Placeholder for future Gemini implementation
        raise NotImplementedError("Gemini provider has not been implemented yet. Set LLM_PROVIDER=openai")
    else:
        raise ValueError(f"Unknown LLM_PROVIDER configuration: {provider_name}")
