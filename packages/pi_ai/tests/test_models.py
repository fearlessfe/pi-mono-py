import pytest
from pi_ai.models import (
    calculate_cost,
    get_model,
    get_models,
    get_providers,
    models_are_equal,
    register_all_models,
    register_anthropic_models,
    register_google_models,
    register_model,
    register_openai_models,
)
from pi_ai.types import Model, ModelCost, Usage, UsageCost


@pytest.fixture(autouse=True)
def clear_registry():
    from pi_ai import models

    models._model_registry.clear()
    yield
    models._model_registry.clear()


class TestModelRegistry:
    def test_register_and_get_model(self):
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            baseUrl="https://api.test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1.0, output=2.0, cacheRead=0.5, cacheWrite=0.5),
            contextWindow=8000,
            maxTokens=1000,
        )

        register_model(model)

        retrieved = get_model("test-provider", "test-model")
        assert retrieved is not None
        assert retrieved.id == "test-model"
        assert retrieved.name == "Test Model"

    def test_get_nonexistent_model(self):
        result = get_model("nonexistent", "model")
        assert result is None

    def test_get_providers(self):
        model1 = Model(
            id="model1",
            name="Model 1",
            api="api1",
            provider="provider1",
            baseUrl="https://api1.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )
        model2 = Model(
            id="model2",
            name="Model 2",
            api="api2",
            provider="provider2",
            baseUrl="https://api2.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )

        register_model(model1)
        register_model(model2)

        providers = get_providers()
        assert "provider1" in providers
        assert "provider2" in providers

    def test_get_models_by_provider(self):
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            baseUrl="https://api.test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )

        register_model(model)

        models = get_models("test-provider")
        assert len(models) == 1
        assert models[0].id == "test-model"

        empty = get_models("nonexistent-provider")
        assert empty == []


class TestPredefinedModels:
    def test_register_openai_models(self):
        register_openai_models()

        providers = get_providers()
        assert "openai" in providers

        models = get_models("openai")
        model_ids = [m.id for m in models]
        assert "gpt-4o" in model_ids
        assert "gpt-4o-mini" in model_ids
        assert "o1" in model_ids

    def test_register_anthropic_models(self):
        register_anthropic_models()

        providers = get_providers()
        assert "anthropic" in providers

        models = get_models("anthropic")
        model_ids = [m.id for m in models]
        assert "claude-3-5-sonnet-20241022" in model_ids

    def test_register_google_models(self):
        register_google_models()

        providers = get_providers()
        assert "google" in providers

        models = get_models("google")
        model_ids = [m.id for m in models]
        assert "gemini-2.0-flash" in model_ids

    def test_register_all_models(self):
        register_all_models()

        providers = get_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers


class TestCalculateCost:
    def test_calculate_cost_basic(self):
        model = Model(
            id="test",
            name="Test",
            api="test",
            provider="test",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=2.0, output=6.0, cacheRead=0.5, cacheWrite=1.0),
            contextWindow=1000,
            maxTokens=100,
        )

        usage = Usage(
            input=500000,
            output=100000,
            cacheRead=200000,
            cacheWrite=100000,
            totalTokens=900000,
            cost=UsageCost(),
        )

        cost = calculate_cost(model, usage)

        assert cost.input == pytest.approx(1.0, rel=1e-6)
        assert cost.output == pytest.approx(0.6, rel=1e-6)
        assert cost.cache_read == pytest.approx(0.1, rel=1e-6)
        assert cost.cache_write == pytest.approx(0.1, rel=1e-6)
        assert cost.total == pytest.approx(1.8, rel=1e-6)


class TestModelsAreEqual:
    def test_same_models(self):
        model1 = Model(
            id="model-id",
            name="Model",
            api="api",
            provider="provider",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )
        model2 = Model(
            id="model-id",
            name="Model",
            api="api",
            provider="provider",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )

        assert models_are_equal(model1, model2) is True

    def test_different_models(self):
        model1 = Model(
            id="model-id-1",
            name="Model 1",
            api="api",
            provider="provider",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )
        model2 = Model(
            id="model-id-2",
            name="Model 2",
            api="api",
            provider="provider",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )

        assert models_are_equal(model1, model2) is False

    def test_none_models(self):
        model = Model(
            id="model-id",
            name="Model",
            api="api",
            provider="provider",
            baseUrl="https://test.com",
            reasoning=False,
            input=["text"],
            cost=ModelCost(input=1, output=1, cacheRead=0, cacheWrite=0),
            contextWindow=1000,
            maxTokens=100,
        )

        assert models_are_equal(None, model) is False
        assert models_are_equal(model, None) is False
        assert models_are_equal(None, None) is False
