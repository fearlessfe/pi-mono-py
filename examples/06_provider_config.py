"""
Using Provider Configurations Example

This example shows how to use the provider configuration helper
to register models with correct base URLs automatically.
"""
import asyncio
import os

from pi_agent import Agent
from pi_ai import Model, ModelCost, get_model
from pi_ai.types import TextContent


async def main():
    print("=" * 60)
    print("Provider Configuration Example")
    print("=" * 60)

    # Import the provider configuration module
    import sys
    from pathlib import Path

    # Add examples directory to path
    examples_dir = str(Path(__file__).parent)
    if examples_dir not in sys.path:
        sys.path.insert(0, examples_dir)

    from providers_config import (
        register_all_providers,
        get_provider_base_url,
    )

    print("\n1. Register all available providers")
    print("-" * 60)

    # Register all providers (will skip those without API keys)
    register_all_providers(
        openai=True,
        anthropic=True,
        google=True,
        groq=True,
    )

    # Show registered providers and models
    from pi_ai import get_providers, get_models

    print("\nRegistered providers:")
    for provider in get_providers():
        models = get_models(provider)
        print(f"\n  {provider}:")
        for model in models[:2]:  # Show first 2 models
            print(f"    - {model.name} ({model.id})")
            print(f"      Base URL: {model.base_url}")
        if len(models) > 2:
            print(f"    ... and {len(models) - 2} more")

    print("\n" + "=" * 60)
    print("2. Getting provider base URLs manually")
    print("-" * 60)

    # Example: Get base URL for a provider
    try:
        openai_url = get_provider_base_url("openai")
        anthropic_url = get_provider_base_url("anthropic")
        google_url = get_provider_base_url("google")

        print(f"\nOpenAI: {openai_url}")
        print(f"Anthropic: {anthropic_url}")
        print(f"Google: {google_url}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("3. Creating a custom model with provider URL")
    print("-" * 60)

    # Example: Create a custom model using provider URL helper
    custom_model = Model(
        id="my-custom-model",
        name="My Custom Model",
        api="openai-completions",
        provider="openai",
        base_url=get_provider_base_url("openai"),
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
        context_window=128000,
        max_tokens=4096,
    )

    print(f"\nCreated custom model: {custom_model.name}")
    print(f"  Base URL: {custom_model.base_url}")
    print(f"  Provider: {custom_model.provider}")

    # Register the custom model
    from pi_ai import register_model
    register_model(custom_model)
    print("  Registered!")

    print("\n" + "=" * 60)
    print("4. Using a registered model with agent")
    print("-" * 60)

    # Get a registered model
    model = get_model("openai", "gpt-4o")

    if model:
        print(f"\nRetrieved model: {model.name}")
        print(f"  ID: {model.id}")
        print(f"  Base URL: {model.base_url}")
        print(f"  API Key Env Var: OPENAI_API_KEY")
    else:
        print("\nModel not found (may need to set API key)")

    print("\n" + "=" * 60)
    print("5. Checking environment variables")
    print("-" * 60)

    # Show which API keys are set
    providers = [
        ("OpenAI", "OPENAI_API_KEY"),
        ("Anthropic", "ANTHROPIC_API_KEY"),
        ("Google", "GEMINI_API_KEY"),
        ("Groq", "GROQ_API_KEY"),
    ]

    print("\nEnvironment Variables:")
    for name, env_var in providers:
        value = os.environ.get(env_var)
        status = "✓ Set" if value else "✗ Not set"
        print(f"  {env_var:25s} {status}")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("""
To use providers:

1. Set environment variables:
   export OPENAI_API_KEY="sk-..."
   export ANTHROPIC_API_KEY="sk-ant-..."
   export GEMINI_API_KEY="..."

2. Use the configuration helper:
   from examples.providers_config import register_all_providers
   register_all_providers()

3. Or use helper to get base URL:
   from examples.providers_config import get_provider_base_url
   url = get_provider_base_url("openai")

4. Get and use registered models:
   from pi_ai import get_model
   model = get_model("openai", "gpt-4o")
   """)


if __name__ == "__main__":
    asyncio.run(main())
