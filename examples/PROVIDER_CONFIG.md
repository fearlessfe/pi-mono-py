# Provider URL 配置指南

## 问题

设置环境变量后，如何找到对应的 URL？

## 解决方案

在 `pi-mono-py` 中，URL 需要在注册模型时指定。我们提供了 `providers_config.py` 配置文件，包含常用 provider 的正确 base URLs。

---

## 方法 1：使用配置助手（推荐）

### 步骤 1：设置环境变量

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GEMINI_API_KEY="..."

# Groq
export GROQ_API_KEY="gsk_..."
```

### 步骤 2：注册 provider 模型

```python
from examples.providers_config import register_all_providers

# 注册所有 provider（会自动跳过没有 API key 的）
register_all_providers()

# 或只注册特定 provider
from examples.providers_config import (
    register_openai_models,
    register_anthropic_models,
    register_google_models,
)

register_openai_models()
```

### 步骤 3：使用注册的模型

```python
from pi_agent import Agent
from pi_ai import get_model

# 获取模型
model = get_model("openai", "gpt-4o")

# 使用模型创建 agent
agent = Agent(options={"model": model})
```

---

## 方法 2：手动获取 provider URL

```python
from examples.providers_config import get_provider_base_url

# 获取 provider 的 base URL
url = get_provider_base_url("openai")
print(url)  # https://api.openai.com/v1

# 在创建模型时使用
from pi_ai import Model, ModelCost, register_model

model = Model(
    id="my-model",
    name="My Model",
    api="openai-completions",
    provider="openai",
    base_url=get_provider_base_url("openai"),
    reasoning=False,
    input=["text"],
    cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
    context_window=128000,
    max_tokens=4096,
)

register_model(model)
```

---

## 预定义的 Provider URLs

| Provider | Base URL |
|----------|-----------|
| OpenAI | `https://api.openai.com/v1` |
| Anthropic | `https://api.anthropic.com` |
| Google | `https://generativelanguage.googleapis.com` |
| Groq | `https://api.groq.com/openai/v1` |
| xAI | `https://api.x.ai/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Cerebras | `https://api.cerebras.ai/v1` |
| DeepSeek | `https://api.deepseek.com` |

---

## 预定义的模型

### OpenAI

- `gpt-4o` - GPT-4o
- `gpt-4o-mini` - GPT-4o Mini
- `gpt-4.1-turbo` - GPT-4.1 Turbo
- `gpt-3.5-turbo` - GPT-3.5 Turbo

### Anthropic

- `claude-3.5-sonnet` - Claude 3.5 Sonnet
- `claude-3.5-haiku` - Claude 3.5 Haiku

### Google

- `gemini-2.5-flash` - Gemini 2.5 Flash
- `gemini-2.5-pro` - Gemini 2.5 Pro

### Groq

- `llama3-70b-8192` - Llama 3 70B
- `mixtral-8x7b-32768` - Mixtral 8x7B

---

## 完整示例

### 示例 1：使用 OpenAI

```python
import asyncio
from pi_agent import Agent
from examples.providers_config import register_openai_models, get_provider_base_url
from pi_ai import get_model

# 注册 OpenAI 模型
register_openai_models()

# 获取模型
model = get_model("openai", "gpt-4o")

# 创建 agent
agent = Agent(options={"model": model})

# 使用
agent.set_system_prompt("You are helpful.")
await agent.prompt("Hello!")
```

### 示例 2：自定义模型

```python
from pi_ai import Model, ModelCost, register_model
from examples.providers_config import get_provider_base_url

# 使用 provider URL 助手
custom_model = Model(
    id="custom-gpt-4",
    name="Custom GPT-4",
    api="openai-completions",
    provider="openai",
    base_url=get_provider_base_url("openai"),
    reasoning=False,
    input=["text"],
    cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
    context_window=128000,
    max_tokens=4096,
)

register_model(custom_model)
```

### 示例 3：检查 API keys

```python
import os

providers = [
    ("OpenAI", "OPENAI_API_KEY"),
    ("Anthropic", "ANTHROPIC_API_KEY"),
    ("Google", "GEMINI_API_KEY"),
]

print("Environment Variables:")
for name, env_var in providers:
    value = os.environ.get(env_var)
    status = "✓ Set" if value else "✗ Not set"
    print(f"  {name:15s} {env_var:25s} {status}")
```

---

## 运行示例

```bash
cd /Users/pengzhen/work/ideas/pi-mono-py

# 查看所有 provider 配置
uv run --directory examples python 06_provider_config.py
```

---

## 常见问题

### Q: 设置了 API key 但仍然报错？

**A**: 确保：
1. 环境变量在 Python 进程启动前设置
2. 环境变量名称正确（区分大小写）
3. 在同一终端会话中运行

### Q: 如何添加新的 provider？

**A**: 在 `examples/providers_config.py` 中添加：

```python
def register_my_provider_models(api_key: str | None = None) -> None:
    base_url = "https://api.myprovider.com/v1"

    register_model(Model(
        id="my-model",
        name="My Model",
        api="my-api",
        provider="my-provider",
        base_url=base_url,
        reasoning=False,
        input=["text"],
        cost=ModelCost(input=0.5, output=1.5, cache_read=0.0, cache_write=0.0),
        context_window=128000,
        max_tokens=4096,
    ))
```

然后在 `PROVIDER_URLS` 中添加 URL，在 `register_all_providers` 中添加调用。

### Q: 为什么 URL 需要手动指定？

**A**: pi-mono-py 的设计理念是：
1. 支持自定义 API endpoint（如代理、内部部署）
2. 支持多个相同 provider 的不同 endpoint（如不同区域）
3. 支持不同 provider 但使用相同 API 格式（如 Groq 使用 OpenAI 格式）

因此需要用户显式指定 URL。

---

## 环境变量映射

| Provider | 环境变量 |
|----------|-----------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` 或 `ANTHROPIC_OAUTH_TOKEN` |
| Google | `GEMINI_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Cerebras | `CEREBRAS_API_KEY` |
| xAI | `XAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| MiniMax | `MINIMAX_API_KEY` |
| HuggingFace | `HF_TOKEN` |

---

## 更多信息

- [Provider Config Example](06_provider_config.py)
- [Quick Start](00_quick_start.py)
- [Simple Agent](01_simple_agent.py)
