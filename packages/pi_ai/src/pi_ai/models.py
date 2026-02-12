from __future__ import annotations

from pi_ai.types import Model, Usage, UsageCost


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
