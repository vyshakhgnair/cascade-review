import os
import pytest
from cascade.cli import build_client, PROVIDER_DEFAULT_MODELS
from cascade.config import DEFAULT_CONFIG


def test_provider_override_uses_provider_default_model():
    os.environ["GROQ_API_KEY"] = "test-key"
    try:
        client = build_client(DEFAULT_CONFIG, "frontier", provider_override="groq")
        assert client.model == PROVIDER_DEFAULT_MODELS["groq"]
    finally:
        del os.environ["GROQ_API_KEY"]


def test_model_override_takes_priority():
    os.environ["GROQ_API_KEY"] = "test-key"
    try:
        client = build_client(DEFAULT_CONFIG, "frontier", provider_override="groq", model_override="custom-model")
        assert client.model == "custom-model"
    finally:
        del os.environ["GROQ_API_KEY"]


def test_same_provider_uses_tier_model():
    os.environ["GROQ_API_KEY"] = "test-key"
    try:
        client = build_client(DEFAULT_CONFIG, "mid", provider_override="groq")
        assert client.model == DEFAULT_CONFIG["models"]["mid"]["model"]
    finally:
        del os.environ["GROQ_API_KEY"]


def test_missing_key_raises():
    env_key = "GROQ_API_KEY"
    old = os.environ.pop(env_key, None)
    try:
        with pytest.raises(RuntimeError, match="No API key"):
            build_client(DEFAULT_CONFIG, "mid")
    finally:
        if old:
            os.environ[env_key] = old


def test_all_providers_have_default_model():
    from cascade.clients.registry import PROVIDERS
    for name in PROVIDERS:
        assert name in PROVIDER_DEFAULT_MODELS, f"Missing default model for {name}"
