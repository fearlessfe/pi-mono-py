from __future__ import annotations

from .types import Model, ModelCost, Usage, UsageCost

_model_registry: dict[str, dict[str, Model]] = {}


def register_model(model: Model) -> None:
    if model.provider not in _model_registry:
        _model_registry[model.provider] = {}
    _model_registry[model.provider][model.id] = model


def get_model(provider: str, model_id: str) -> Model | None:
    provider_models = _model_registry.get(provider)
    if provider_models is None:
        return None
    return provider_models.get(model_id)


def get_providers() -> list[str]:
    return list(_model_registry.keys())


def get_models(provider: str) -> list[Model]:
    provider_models = _model_registry.get(provider)
    if provider_models is None:
        return []
    return list(provider_models.values())


def calculate_cost(model: Model, usage: Usage) -> UsageCost:
    return UsageCost(
        input=(model.cost.input / 1_000_000) * usage.input,
        output=(model.cost.output / 1_000_000) * usage.output,
        cacheRead=(model.cost.cache_read / 1_000_000) * usage.cache_read,
        cacheWrite=(model.cost.cache_write / 1_000_000) * usage.cache_write,
        total=(
            (model.cost.input / 1_000_000) * usage.input
            + (model.cost.output / 1_000_000) * usage.output
            + (model.cost.cache_read / 1_000_000) * usage.cache_read
            + (model.cost.cache_write / 1_000_000) * usage.cache_write
        ),
    )


def models_are_equal(a: Model | None, b: Model | None) -> bool:
    if a is None or b is None:
        return False
    return a.id == b.id and a.provider == b.provider


def register_openai_models(base_url: str = "https://api.openai.com/v1") -> None:
    openai_models = [
        Model(
            id="gpt-4o",
            name="GPT-4o",
            api="openai-completions",
            provider="openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.50, output=10.00, cacheRead=1.25, cacheWrite=1.25),
            contextWindow=128000,
            maxTokens=16384,
        ),
        Model(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            api="openai-completions",
            provider="openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cacheRead=0.075, cacheWrite=0.075),
            contextWindow=128000,
            maxTokens=16384,
        ),
        Model(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            api="openai-completions",
            provider="openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=10.00, output=30.00, cacheRead=0.0, cacheWrite=0.0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="o1",
            name="o1",
            api="openai-responses",
            provider="openai",
            baseUrl=base_url,
            reasoning=True,
            input=["text", "image"],
            cost=ModelCost(input=15.00, output=60.00, cacheRead=7.50, cacheWrite=7.50),
            contextWindow=200000,
            maxTokens=100000,
        ),
        Model(
            id="o1-mini",
            name="o1 Mini",
            api="openai-responses",
            provider="openai",
            baseUrl=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=1.10, output=4.40, cacheRead=0.55, cacheWrite=0.55),
            contextWindow=128000,
            maxTokens=65536,
        ),
        Model(
            id="o3-mini",
            name="o3 Mini",
            api="openai-responses",
            provider="openai",
            baseUrl=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=1.10, output=4.40, cacheRead=0.55, cacheWrite=0.55),
            contextWindow=200000,
            maxTokens=100000,
        ),
    ]
    for model in openai_models:
        register_model(model)


def register_anthropic_models(base_url: str = "https://api.anthropic.com") -> None:
    anthropic_models = [
        Model(
            id="claude-sonnet-4-20250514",
            name="Claude Sonnet 4",
            api="anthropic-messages",
            provider="anthropic",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cacheRead=0.30, cacheWrite=3.75),
            contextWindow=200000,
            maxTokens=16000,
        ),
        Model(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            api="anthropic-messages",
            provider="anthropic",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cacheRead=0.30, cacheWrite=3.75),
            contextWindow=200000,
            maxTokens=8192,
        ),
        Model(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            api="anthropic-messages",
            provider="anthropic",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.80, output=4.00, cacheRead=0.08, cacheWrite=1.00),
            contextWindow=200000,
            maxTokens=8192,
        ),
        Model(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            api="anthropic-messages",
            provider="anthropic",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=15.00, output=75.00, cacheRead=1.50, cacheWrite=18.75),
            contextWindow=200000,
            maxTokens=4096,
        ),
    ]
    for model in anthropic_models:
        register_model(model)


def register_google_models(base_url: str = "https://generativelanguage.googleapis.com") -> None:
    google_models = [
        Model(
            id="gemini-2.5-flash-preview-05-20",
            name="Gemini 2.5 Flash",
            api="google-generative-ai",
            provider="google",
            baseUrl=base_url,
            reasoning=True,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cacheRead=0.0375, cacheWrite=0.0375),
            contextWindow=1000000,
            maxTokens=65536,
        ),
        Model(
            id="gemini-2.0-flash",
            name="Gemini 2.0 Flash",
            api="google-generative-ai",
            provider="google",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.10, output=0.40, cacheRead=0.025, cacheWrite=0.025),
            contextWindow=1000000,
            maxTokens=8192,
        ),
        Model(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            api="google-generative-ai",
            provider="google",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=1.25, output=5.00, cacheRead=0.3125, cacheWrite=0.3125),
            contextWindow=2000000,
            maxTokens=8192,
        ),
        Model(
            id="gemini-1.5-flash",
            name="Gemini 1.5 Flash",
            api="google-generative-ai",
            provider="google",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.075, output=0.30, cacheRead=0.01875, cacheWrite=0.01875),
            contextWindow=1000000,
            maxTokens=8192,
        ),
    ]
    for model in google_models:
        register_model(model)


def register_zhipu_models(base_url: str = "https://open.bigmodel.cn/api/paas/v4") -> None:
    zhipu_models = [
        Model(
            id="glm-4-plus",
            name="GLM-4 Plus",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.05, output=0.05, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4-0520",
            name="GLM-4 0520",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.10, output=0.10, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4-air",
            name="GLM-4 Air",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.001, output=0.001, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4-airx",
            name="GLM-4 AirX",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.001, output=0.001, cacheRead=0, cacheWrite=0),
            contextWindow=8000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4-flash",
            name="GLM-4 Flash",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.0001, output=0.0001, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4-long",
            name="GLM-4 Long",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.001, output=0.001, cacheRead=0, cacheWrite=0),
            contextWindow=1000000,
            maxTokens=4096,
        ),
        Model(
            id="glm-4v-plus",
            name="GLM-4V Plus",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.01, output=0.01, cacheRead=0, cacheWrite=0),
            contextWindow=8000,
            maxTokens=1024,
        ),
        Model(
            id="glm-4v-flash",
            name="GLM-4V Flash",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.0001, output=0.0001, cacheRead=0, cacheWrite=0),
            contextWindow=8000,
            maxTokens=1024,
        ),
        Model(
            id="glm-z1-air",
            name="GLM-Z1 Air",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=0.001, output=0.001, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="glm-z1-airx",
            name="GLM-Z1 AirX",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=0.001, output=0.001, cacheRead=0, cacheWrite=0),
            contextWindow=8000,
            maxTokens=4096,
        ),
        Model(
            id="glm-z1-flash",
            name="GLM-Z1 Flash",
            api="zhipu-chat",
            provider="zhipu",
            baseUrl=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=0.0001, output=0.0001, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
    ]
    for model in zhipu_models:
        register_model(model)


def register_azure_openai_models(azure_resource: str = "your-resource-name") -> None:
    """Register Azure OpenAI models.

    Note: Azure OpenAI requires deployment-based URLs. The base_url should be
    https://{resource-name}.openai.azure.com and model.id should be {deployment-id}.
    Users should call register_model() with their specific deployment names.
    """
    base_url = f"https://{azure_resource}.openai.azure.com"
    azure_models = [
        Model(
            id="gpt-4o",
            name="GPT-4o (Azure)",
            api="azure-openai-responses",
            provider="azure-openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.50, output=10.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="gpt-4o-mini",
            name="GPT-4o Mini (Azure)",
            api="azure-openai-responses",
            provider="azure-openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="gpt-4-turbo",
            name="GPT-4 Turbo (Azure)",
            api="azure-openai-responses",
            provider="azure-openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=10.00, output=30.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="gpt-35-turbo",
            name="GPT-3.5 Turbo (Azure)",
            api="azure-openai-responses",
            provider="azure-openai",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.50, output=1.50, cacheRead=0, cacheWrite=0),
            contextWindow=16384,
            maxTokens=4096,
        ),
    ]
    for model in azure_models:
        register_model(model)


def register_all_models(
    openai_base_url: str = "https://api.openai.com/v1",
    anthropic_base_url: str = "https://api.anthropic.com",
    google_base_url: str = "https://generativelanguage.googleapis.com",
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    mistral_base_url: str = "https://api.mistral.ai/v1",
    xai_base_url: str = "https://api.x.ai/v1",
    openrouter_base_url: str = "https://openrouter.ai/api/v1",
    azure_resource: str = "your-resource-name",
) -> None:
    register_openai_models(openai_base_url)
    register_anthropic_models(anthropic_base_url)
    register_google_models(google_base_url)
    register_zhipu_models(zhipu_base_url)
    register_mistral_models(mistral_base_url)
    register_xai_models(xai_base_url)
    register_openrouter_models(openrouter_base_url)
    register_azure_openai_models(azure_resource)


def register_mistral_models(base_url: str = "https://api.mistral.ai/v1") -> None:
    """Register Mistral AI models."""
    mistral_models = [
        Model(
            id="mistral-large-latest",
            name="Mistral Large",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.00, output=6.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
        Model(
            id="mistral-medium-latest",
            name="Mistral Medium",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.40, output=2.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
        Model(
            id="mistral-small-latest",
            name="Mistral Small",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.10, output=0.30, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
        Model(
            id="codestral-latest",
            name="Codestral",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.20, output=0.60, cacheRead=0, cacheWrite=0),
            contextWindow=256000,
            maxTokens=8192,
        ),
        Model(
            id="ministral-8b-latest",
            name="Ministral 8B",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.10, output=0.10, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
        Model(
            id="ministral-3b-latest",
            name="Ministral 3B",
            api="mistral-chat",
            provider="mistral",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.04, output=0.04, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
    ]
    for model in mistral_models:
        register_model(model)


def register_xai_models(base_url: str = "https://api.x.ai/v1") -> None:
    """Register xAI (Grok) models."""
    xai_models = [
        Model(
            id="grok-2-latest",
            name="Grok 2",
            api="xai-chat",
            provider="xai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.00, output=10.00, cacheRead=0, cacheWrite=0),
            contextWindow=131072,
            maxTokens=8192,
        ),
        Model(
            id="grok-2-vision-latest",
            name="Grok 2 Vision",
            api="xai-chat",
            provider="xai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.00, output=10.00, cacheRead=0, cacheWrite=0),
            contextWindow=32768,
            maxTokens=8192,
        ),
        Model(
            id="grok-beta",
            name="Grok Beta",
            api="xai-chat",
            provider="xai",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=5.00, output=15.00, cacheRead=0, cacheWrite=0),
            contextWindow=131072,
            maxTokens=8192,
        ),
        Model(
            id="grok-2-1212",
            name="Grok 2 1212",
            api="xai-chat",
            provider="xai",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.00, output=10.00, cacheRead=0, cacheWrite=0),
            contextWindow=131072,
            maxTokens=8192,
        ),
    ]
    for model in xai_models:
        register_model(model)


def register_openrouter_models(base_url: str = "https://openrouter.ai/api/v1") -> None:
    """Register OpenRouter gateway models.

    Note: OpenRouter provides access to many models through their gateway.
    Here we register some popular ones. Users can add more as needed.
    """
    openrouter_models = [
        Model(
            id="anthropic/claude-sonnet-4",
            name="Claude Sonnet 4 (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cacheRead=0, cacheWrite=0),
            contextWindow=200000,
            maxTokens=8192,
        ),
        Model(
            id="anthropic/claude-3.5-sonnet",
            name="Claude 3.5 Sonnet (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cacheRead=0, cacheWrite=0),
            contextWindow=200000,
            maxTokens=8192,
        ),
        Model(
            id="openai/gpt-4o",
            name="GPT-4o (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.50, output=10.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="openai/gpt-4o-mini",
            name="GPT-4o Mini (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=4096,
        ),
        Model(
            id="google/gemini-pro-1.5",
            name="Gemini 1.5 Pro (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=1.25, output=5.00, cacheRead=0, cacheWrite=0),
            contextWindow=1000000,
            maxTokens=8192,
        ),
        Model(
            id="meta-llama/llama-3.1-70b-instruct",
            name="Llama 3.1 70B (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=0.52, output=0.75, cacheRead=0, cacheWrite=0),
            contextWindow=131072,
            maxTokens=8192,
        ),
        Model(
            id="mistralai/mistral-large",
            name="Mistral Large (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.00, output=6.00, cacheRead=0, cacheWrite=0),
            contextWindow=128000,
            maxTokens=8192,
        ),
        Model(
            id="x-ai/grok-beta",
            name="Grok Beta (OpenRouter)",
            api="openrouter-chat",
            provider="openrouter",
            baseUrl=base_url,
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=5.00, output=15.00, cacheRead=0, cacheWrite=0),
            contextWindow=131072,
            maxTokens=8192,
        ),
    ]
    for model in openrouter_models:
        register_model(model)
