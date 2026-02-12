from __future__ import annotations

from pi_ai.types import Model, ModelCost, Usage, UsageCost


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
        cache_read=(model.cost.cache_read / 1_000_000) * usage.cache_read,
        cache_write=(model.cost.cache_write / 1_000_000) * usage.cache_write,
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
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=2.50, output=10.00, cache_read=1.25, cache_write=1.25),
            context_window=128000,
            max_tokens=16384,
        ),
        Model(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            api="openai-completions",
            provider="openai",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cache_read=0.075, cache_write=0.075),
            context_window=128000,
            max_tokens=16384,
        ),
        Model(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            api="openai-completions",
            provider="openai",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=10.00, output=30.00, cache_read=0.0, cache_write=0.0),
            context_window=128000,
            max_tokens=4096,
        ),
        Model(
            id="o1",
            name="o1",
            api="openai-responses",
            provider="openai",
            base_url=base_url,
            reasoning=True,
            input=["text", "image"],
            cost=ModelCost(input=15.00, output=60.00, cache_read=7.50, cache_write=7.50),
            context_window=200000,
            max_tokens=100000,
        ),
        Model(
            id="o1-mini",
            name="o1 Mini",
            api="openai-responses",
            provider="openai",
            base_url=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=1.10, output=4.40, cache_read=0.55, cache_write=0.55),
            context_window=128000,
            max_tokens=65536,
        ),
        Model(
            id="o3-mini",
            name="o3 Mini",
            api="openai-responses",
            provider="openai",
            base_url=base_url,
            reasoning=True,
            input=["text"],
            cost=ModelCost(input=1.10, output=4.40, cache_read=0.55, cache_write=0.55),
            context_window=200000,
            max_tokens=100000,
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
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cache_read=0.30, cache_write=3.75),
            context_window=200000,
            max_tokens=16000,
        ),
        Model(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            api="anthropic-messages",
            provider="anthropic",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=3.00, output=15.00, cache_read=0.30, cache_write=3.75),
            context_window=200000,
            max_tokens=8192,
        ),
        Model(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            api="anthropic-messages",
            provider="anthropic",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.80, output=4.00, cache_read=0.08, cache_write=1.00),
            context_window=200000,
            max_tokens=8192,
        ),
        Model(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            api="anthropic-messages",
            provider="anthropic",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=15.00, output=75.00, cache_read=1.50, cache_write=18.75),
            context_window=200000,
            max_tokens=4096,
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
            base_url=base_url,
            reasoning=True,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.60, cache_read=0.0375, cache_write=0.0375),
            context_window=1000000,
            max_tokens=65536,
        ),
        Model(
            id="gemini-2.0-flash",
            name="Gemini 2.0 Flash",
            api="google-generative-ai",
            provider="google",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.10, output=0.40, cache_read=0.025, cache_write=0.025),
            context_window=1000000,
            max_tokens=8192,
        ),
        Model(
            id="gemini-1.5-pro",
            name="Gemini 1.5 Pro",
            api="google-generative-ai",
            provider="google",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=1.25, output=5.00, cache_read=0.3125, cache_write=0.3125),
            context_window=2000000,
            max_tokens=8192,
        ),
        Model(
            id="gemini-1.5-flash",
            name="Gemini 1.5 Flash",
            api="google-generative-ai",
            provider="google",
            base_url=base_url,
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.075, output=0.30, cache_read=0.01875, cache_write=0.01875),
            context_window=1000000,
            max_tokens=8192,
        ),
    ]
    for model in google_models:
        register_model(model)


def register_all_models(
    openai_base_url: str = "https://api.openai.com/v1",
    anthropic_base_url: str = "https://api.anthropic.com",
    google_base_url: str = "https://generativelanguage.googleapis.com",
) -> None:
    register_openai_models(openai_base_url)
    register_anthropic_models(anthropic_base_url)
    register_google_models(google_base_url)
