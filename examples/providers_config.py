"""
Provider configurations for common LLM providers.

This module provides pre-configured models with correct base URLs.
You can use these directly or as a reference for your own configurations.
"""
from pi_ai import Model, ModelCost, register_model


# ============================================================================
# OpenAI
# ============================================================================

def register_openai_models(api_key: str | None = None) -> None:
    """Register OpenAI models with default base URLs."""
    base_url = "https://api.openai.com/v1"

    # GPT-4o models
    register_model(Model(
        id="gpt-4o",
        name="GPT-4o",
        api="openai-completions",
        provider="openai",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=2.5, output=10.0, cache_read=1.25, cache_write=0.625),
        context_window=128000,
        max_tokens=4096,
    ))

    register_model(Model(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        api="openai-completions",
        provider="openai",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=0.15, output=0.60, cache_read=0.075, cache_write=0.0375),
        context_window=128000,
        max_tokens=16384,
    ))

    # GPT-4.1 models
    register_model(Model(
        id="gpt-4.1-turbo",
        name="GPT-4.1 Turbo",
        api="openai-completions",
        provider="openai",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=0.5, output=2.0, cache_read=0.25, cache_write=0.125),
        context_window=128000,
        max_tokens=4096,
    ))

    # GPT-3.5 models
    register_model(Model(
        id="gpt-3.5-turbo",
        name="GPT-3.5 Turbo",
        api="openai-completions",
        provider="openai",
        base_url=base_url,
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=2.0, cache_read=0.0, cache_write=0.0),
        context_window=16384,
        max_tokens=4096,
    ))


# ============================================================================
# Anthropic
# ============================================================================

def register_anthropic_models(api_key: str | None = None) -> None:
    """Register Anthropic models with default base URLs."""
    base_url = "https://api.anthropic.com"

    # Claude 3.5 models
    register_model(Model(
        id="claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        api="anthropic-messages",
        provider="anthropic",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=3.0, output=15.0, cache_read=0.15, cache_write=1.5),
        context_window=200000,
        max_tokens=8192,
    ))

    register_model(Model(
        id="claude-3.5-haiku",
        name="Claude 3.5 Haiku",
        api="anthropic-messages",
        provider="anthropic",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=0.25, output=1.25, cache_read=0.01, cache_write=0.10),
        context_window=200000,
        max_tokens=8192,
    ))


# ============================================================================
# Google
# ============================================================================

def register_google_models(api_key: str | None = None) -> None:
    """Register Google Gemini models with default base URLs."""
    base_url = "https://generativelanguage.googleapis.com"

    # Gemini 2.0 models
    register_model(Model(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        api="google-generative-ai",
        provider="google",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
        context_window=1000000,
        max_tokens=8192,
    ))

    register_model(Model(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        api="google-generative-ai",
        provider="google",
        base_url=base_url,
        reasoning=False,
        input=["text", "image"],
        cost=ModelCost(input=0.0, output=0.0, cache_read=0.0, cache_write=0.0),
        context_window=1000000,
        max_tokens=8192,
    ))


# ============================================================================
# Groq (uses OpenAI-compatible API)
# ============================================================================

def register_groq_models(api_key: str | None = None) -> None:
    """Register Groq models with their base URL."""
    base_url = "https://api.groq.com/openai/v1"

    register_model(Model(
        id="llama3-70b-8192",
        name="Llama 3 70B",
        api="openai-completions",
        provider="groq",
        base_url=base_url,
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.19, output=0.19, cache_read=0.0, cache_write=0.0),
        context_window=131072,
        max_tokens=8192,
    ))

    register_model(Model(
        id="mixtral-8x7b-32768",
        name="Mixtral 8x7B",
        api="openai-completions",
        provider="groq",
        base_url=base_url,
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.24, output=0.24, cache_read=0.0, cache_write=0.0),
        context_window=32768,
        max_tokens=32768,
    ))


# ============================================================================
# Register all providers
# ============================================================================

def register_all_providers(
    openai: bool = True,
    anthropic: bool = True,
    google: bool = True,
    groq: bool = True,
) -> None:
    """
    Register all available providers.

    Args:
        openai: Register OpenAI models (requires OPENAI_API_KEY)
        anthropic: Register Anthropic models (requires ANTHROPIC_API_KEY)
        google: Register Google models (requires GEMINI_API_KEY)
        groq: Register Groq models (requires GROQ_API_KEY)
    """
    import os

    if openai:
        if os.environ.get("OPENAI_API_KEY"):
            register_openai_models()
        else:
            print("Skipping OpenAI: OPENAI_API_KEY not set")

    if anthropic:
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_OAUTH_TOKEN"):
            register_anthropic_models()
        else:
            print("Skipping Anthropic: ANTHROPIC_API_KEY not set")

    if google:
        if os.environ.get("GEMINI_API_KEY"):
            register_google_models()
        else:
            print("Skipping Google: GEMINI_API_KEY not set")

    if groq:
        if os.environ.get("GROQ_API_KEY"):
            register_groq_models()
        else:
            print("Skipping Groq: GROQ_API_KEY not set")


# ============================================================================
# Provider URL Reference (for custom configurations)
# ============================================================================

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com",
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "deepseek": "https://api.deepseek.com",
}


def get_provider_base_url(provider: str) -> str:
    """
    Get the base URL for a given provider.

    Args:
        provider: Provider name (e.g., "openai", "anthropic", "google")

    Returns:
        Base URL for the provider's API
    """
    url = PROVIDER_URLS.get(provider)
    if not url:
        raise ValueError(f"Unknown provider: {provider}")
    return url
