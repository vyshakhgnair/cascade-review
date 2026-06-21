from cascade.clients.openai_compatible import OpenAICompatibleClient
from cascade.clients.anthropic import AnthropicClient
from cascade.clients.gemini import GeminiClient
from cascade.clients.ollama import OllamaClient
from cascade.clients.base import BaseClient

PROVIDERS = {
    "ollama":     {"cls": OllamaClient,          "base_url": "http://localhost:11434"},
    "openai":     {"cls": OpenAICompatibleClient, "base_url": "https://api.openai.com/v1"},
    "groq":       {"cls": OpenAICompatibleClient, "base_url": "https://api.groq.com/openai/v1"},
    "deepseek":   {"cls": OpenAICompatibleClient, "base_url": "https://api.deepseek.com/v1"},
    "openrouter": {"cls": OpenAICompatibleClient, "base_url": "https://openrouter.ai/api/v1"},
    "mistral":    {"cls": OpenAICompatibleClient, "base_url": "https://api.mistral.ai/v1"},
    "together":   {"cls": OpenAICompatibleClient, "base_url": "https://api.together.xyz/v1"},
    "anthropic":  {"cls": AnthropicClient,        "base_url": "https://api.anthropic.com"},
    "gemini":     {"cls": GeminiClient,           "base_url": "https://generativelanguage.googleapis.com"},
}

def get_client(provider: str, model: str, api_key: str = None, base_url: str = None) -> BaseClient:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Available: {', '.join(PROVIDERS)}")
    entry = PROVIDERS[provider]
    return entry["cls"](model=model, api_key=api_key, base_url=base_url or entry["base_url"])
