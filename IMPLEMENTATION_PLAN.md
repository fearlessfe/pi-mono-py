# pi-mono-py 完整实现规划

## 1. 项目概述

### 1.1 目标
将 TypeScript 项目 [pi-mono](https://github.com/badlogic/pi-mono) 完整移植到 Python，提供：
- 统一的多提供商 LLM API
- Agent 运行时和工具执行框架
- 可扩展的插件系统

### 1.2 原始 pi-mono 包结构

| 包名 | 功能 | 优先级 |
|------|------|--------|
| **pi-ai** | 统一多提供商 LLM API | P0 - 核心 |
| **pi-agent-core** | Agent 运行时 | P0 - 核心 |
| **pi-coding-agent** | 交互式编码代理 CLI | P1 - 重要 |
| **pi-tui** | 终端 UI 库 | P2 - 可选 |
| **pi-web-ui** | Web UI 组件 | P3 - 后期 |
| **pi-mom** | Slack 机器人 | P3 - 后期 |
| **pi-pods** | vLLM 部署 CLI | P3 - 后期 |

### 1.3 当前 pi-mono-py 实现状态

| 模块 | 状态 | 完成度 |
|------|------|--------|
| **pi-ai/types.py** | 基础类型定义 | 60% |
| **pi-ai/event_stream.py** | 异步事件流 | 70% |
| **pi-ai/models.py** | 模型注册表 | 40% |
| **pi-ai/providers/openai.py** | OpenAI Provider | 30% |
| **pi-ai/providers/anthropic.py** | Anthropic Provider | 30% |
| **pi-ai/providers/google.py** | Google Provider | 30% |
| **pi-ai/providers/transform.py** | 跨提供商转换 | 20% |
| **pi-agent/agent.py** | Agent 类 | 50% |
| **pi-agent/loop.py** | Agent 循环 | 40% |
| **pi-agent/types.py** | Agent 类型 | 60% |

---

## 2. 实现阶段规划

### Phase 0: 基础设施 (1-2 天)

#### 目标
- 完善项目结构
- 建立测试框架
- 配置 CI/CD

#### 任务清单
- [ ] 完善 pyproject.toml 配置
  - [ ] 添加完整依赖声明
  - [ ] 配置 mypy/pyright 类型检查
  - [ ] 配置 ruff 代码风格
- [ ] 建立测试基础设施
  - [ ] pytest 配置完善
  - [ ] 测试覆盖率报告
  - [ ] Mock 策略定义
- [ ] 文档结构
  - [ ] API 文档生成 (Sphinx/MkDocs)
  - [ ] 贡献指南
  - [ ] 更新日志

#### 交付物
```
pi-mono-py/
├── docs/
│   ├── api/
│   ├── contributing.md
│   └── changelog.md
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   └── mocks/
├── pyproject.toml (完善)
└── .github/
    └── workflows/
        └── ci.yml
```

---

### Phase 1: pi-ai 核心类型系统 (3-5 天)

#### 目标
完整实现所有核心类型定义，与 TypeScript 版本对齐

#### 1.1 基础类型 (types.py)

```python
# 需要完善的类型
- ThinkingLevel        ✓ 已有
- CacheRetention       ✓ 已有
- StopReason          ✓ 已有
- KnownApi            ✓ 已有
- KnownProvider       ✓ 已有

# 需要新增/完善的类型
- ThinkingBudgets     部分完成
- StreamOptions       部分完成
- SimpleStreamOptions 部分完成
```

#### 1.2 内容类型

```python
# 已完成
- TextContent         ✓
- ThinkingContent     ✓
- ImageContent        ✓
- ToolCall            ✓

# 需要验证
- AssistantContent    Union 类型，需要验证所有子类型
- UserContent         Union 类型，需要验证所有子类型
- ToolResultContent   Union 类型，需要验证所有子类型
```

#### 1.3 使用量和成本

```python
- Usage               ✓ 已有
- UsageCost           ✓ 已有
- ModelCost           ✓ 已有

# 需要添加
- calculate_cost()    ✓ 已有，需要验证计算逻辑
```

#### 1.4 消息类型

```python
- UserMessage         ✓ 已有
- AssistantMessage    ✓ 已有
- ToolResultMessage   ✓ 已有
- Message             ✓ Union 类型

# 需要验证
- 消息序列化/反序列化
- Pydantic 验证规则
```

#### 1.5 事件类型 (完整实现)

```python
# 当前状态：部分实现
# 需要：12 种事件类型

- StartEvent          需要验证
- TextStartEvent      需要验证
- TextDeltaEvent      需要验证
- TextEndEvent        需要验证
- ThinkingStartEvent  需要验证
- ThinkingDeltaEvent  需要验证
- ThinkingEndEvent    需要验证
- ToolcallStartEvent  需要验证
- ToolcallDeltaEvent  需要验证
- ToolcallEndEvent    需要验证
- DoneEvent           需要验证
- ErrorEvent          需要验证
```

#### 任务清单
- [ ] 完善 types.py 中所有类型定义
- [ ] 添加完整的 Pydantic 验证
- [ ] 添加类型别名导出
- [ ] 编写类型测试用例
- [ ] 验证序列化/反序列化

#### 测试要求
- [ ] 所有类型的创建测试
- [ ] Pydantic 验证测试
- [ ] JSON 序列化/反序列化测试
- [ ] 边界条件测试

---

### Phase 2: pi-ai 事件流系统 (2-3 天)

#### 目标
完整实现异步事件流系统

#### 2.1 EventStream 基类

```python
class EventStream(Generic[T, R]):
    """
    泛型事件流
    
    - push(event): 推送事件
    - end(result): 结束流
    - __aiter__(): 异步迭代
    - result(): 获取最终结果
    """
```

#### 2.2 AssistantMessageEventStream

```python
class AssistantMessageEventStream(EventStream[AssistantMessageEvent, AssistantMessage]):
    """
    LLM 响应事件流
    
    - 自动检测 done/error 事件
    - 提取最终 AssistantMessage
    """
```

#### 任务清单
- [ ] 完善 EventStream 实现
  - [ ] 错误处理
  - [ ] 取消支持
  - [ ] 超时处理
- [ ] 完善 AssistantMessageEventStream
  - [ ] 事件类型判断
  - [ ] 结果提取
- [ ] 添加流工具函数
  - [ ] collect_events()
  - [ ] stream_to_list()
  - [ ] async_generator_wrapper()

#### 测试要求
- [ ] 基本流程测试
- [ ] 错误处理测试
- [ ] 取消测试
- [ ] 并发测试

---

### Phase 3: pi-ai Provider 实现 (5-7 天)

#### 目标
完整实现所有主要 LLM 提供商

#### 3.1 Provider 接口

```python
class Provider(Protocol):
    """Provider 协议"""
    
    @property
    def api(self) -> str:
        """API 标识符"""
        ...
    
    def stream(
        self,
        model: Model,
        context: Context,
        options: StreamOptions | None = None
    ) -> AssistantMessageEventStream:
        """流式响应"""
        ...
    
    def stream_simple(
        self,
        model: Model,
        context: Context,
        options: SimpleStreamOptions | None = None
    ) -> AssistantMessageEventStream:
        """简化流式响应（支持 thinking）"""
        ...
```

#### 3.2 OpenAI Provider

```python
# packages/pi_ai/src/pi_ai/providers/openai.py

# 需要实现的功能
- [ ] Chat Completions API
  - [ ] 文本生成
  - [ ] 流式响应
  - [ ] 工具调用
  - [ ] 图片输入
  
- [ ] Responses API (o1/o3 模型)
  - [ ] reasoning_effort 参数
  - [ ] 非流式响应
  - [ ] thinking 事件转换
  
- [ ] 错误处理
  - [ ] 重试逻辑
  - [ ] 超时处理
  - [ ] 错误事件
  
- [ ] 成本计算
  - [ ] 输入/输出 token
  - [ ] 缓存 token
  - [ ] 价格计算
```

#### 3.3 Anthropic Provider

```python
# packages/pi_ai/src/pi_ai/providers/anthropic.py

# 需要实现的功能
- [ ] Messages API
  - [ ] 文本生成
  - [ ] 流式响应
  - [ ] 工具调用
  - [ ] 图片输入
  
- [ ] Thinking Blocks
  - [ ] thinking_enabled 参数
  - [ ] thinking_budget_tokens 参数
  - [ ] thinking 事件流
  
- [ ] 错误处理
  - [ ] 重试逻辑
  - [ ] 超时处理
  - [ ] 错误事件
  
- [ ] OAuth 支持
  - [ ] ANTHROPIC_OAUTH_TOKEN
  - [ ] 令牌刷新
```

#### 3.4 Google Provider

```python
# packages/pi_ai/src/pi_ai/providers/google.py

# 需要实现的功能
- [ ] Generative AI API
  - [ ] 文本生成
  - [ ] 流式响应
  - [ ] 工具调用
  - [ ] 图片输入
  
- [ ] Vertex AI
  - [ ] ADC 认证
  - [ ] 项目配置
  - [ ] 区域配置
  
- [ ] 错误处理
  - [ ] 重试逻辑
  - [ ] 超时处理
  - [ ] 错误事件
```

#### 3.5 其他 Provider (按优先级)

```python
# P1: 重要
- [ ] Groq (OpenAI 兼容)
- [ ] Mistral (OpenAI 兼容)
- [ ] xAI (OpenAI 兼容)

# P2: 可选
- [ ] Cerebras
- [ ] OpenRouter
- [ ] Azure OpenAI
- [ ] Amazon Bedrock

# P3: 后期
- [ ] GitHub Copilot (OAuth)
- [ ] Google Gemini CLI (OAuth)
- [ ] Vercel AI Gateway
```

#### 3.6 跨提供商消息转换 (transform.py)

```python
# packages/pi_ai/src/pi_ai/providers/transform.py

# 需要实现的功能
- [ ] transform_messages()
  - [ ] thinking 块转换 (Claude → GPT)
  - [ ] 工具调用 ID 规范化
  - [ ] 消息格式适配
  
- [ ] normalize_tool_call_id()
  - [ ] Mistral 格式
  - [ ] 其他 provider 格式
  
- [ ] is_same_model()
  - [ ] 模型比较逻辑
```

#### 测试要求
- [ ] 每个 Provider 的单元测试
- [ ] Mock HTTP 响应测试
- [ ] 错误处理测试
- [ ] 消息转换测试
- [ ] 集成测试（真实 API）

---

### Phase 4: pi-ai 模型注册表 (2-3 天)

#### 目标
完善模型注册和管理系统

#### 4.1 模型注册

```python
# packages/pi_ai/src/pi_ai/models.py

# 需要实现的功能
- [ ] register_model(model: Model)
- [ ] get_model(provider: str, model_id: str) -> Model | None
- [ ] get_models(provider: str) -> list[Model]
- [ ] get_providers() -> list[str]
- [ ] unregister_model(provider: str, model_id: str)
- [ ] clear_models()

# 预定义模型
- [ ] OpenAI 模型 (gpt-4o, gpt-4o-mini, etc.)
- [ ] Anthropic 模型 (claude-3.5-sonnet, etc.)
- [ ] Google 模型 (gemini-2.5-flash, etc.)
- [ ] Groq 模型
- [ ] 其他 provider 模型
```

#### 4.2 成本计算

```python
# 需要验证
- [ ] calculate_cost(model: Model, usage: Usage) -> UsageCost
  - [ ] 输入 token 成本
  - [ ] 输出 token 成本
  - [ ] 缓存读取成本
  - [ ] 缓存写入成本
  - [ ] 总成本计算
```

#### 4.3 API Key 管理

```python
# packages/pi_ai/src/pi_ai/env_keys.py

# 需要实现
- [ ] get_env_api_key(provider: str) -> str | None
  - [ ] 环境变量映射
  - [ ] OAuth 令牌支持
  - [ ] ADC 凭证支持 (Vertex AI)
  - [ ] AWS 凭证支持 (Bedrock)
```

#### 测试要求
- [ ] 模型注册测试
- [ ] 模型查询测试
- [ ] 成本计算测试
- [ ] API Key 解析测试

---

### Phase 5: pi-ai 流式 API (2-3 天)

#### 目标
完善流式和完成 API

#### 5.1 核心 API

```python
# packages/pi_ai/src/pi_ai/stream.py

# 需要实现
- [ ] stream(model, context, options) -> AssistantMessageEventStream
- [ ] complete(model, context, options) -> AssistantMessage
- [ ] stream_simple(model, context, options) -> AssistantMessageEventStream
- [ ] complete_simple(model, context, options) -> AssistantMessage
```

#### 5.2 Provider 注册表

```python
# packages/pi_ai/src/pi_ai/registry.py

# 需要实现
- [ ] register_api_provider(provider, source_id)
- [ ] get_api_provider(api: str) -> Provider | None
- [ ] get_api_providers() -> list[Provider]
- [ ] unregister_api_providers(source_id)
- [ ] clear_api_providers()
```

#### 测试要求
- [ ] stream() 测试
- [ ] complete() 测试
- [ ] Provider 选择测试
- [ ] 错误处理测试

---

### Phase 6: pi-agent 核心实现 (5-7 天)

#### 目标
完整实现 Agent 运行时

#### 6.1 Agent 类型系统

```python
# packages/pi_agent/src/pi_agent/types.py

# 需要完善
- [ ] AgentMessage (支持扩展)
- [ ] AgentState
  - [ ] systemPrompt
  - [ ] model
  - [ ] thinkingLevel
  - [ ] tools
  - [ ] messages
  - [ ] isStreaming
  - [ ] streamMessage
  - [ ] pendingToolCalls
  - [ ] error
  
- [ ] AgentEvent (所有事件类型)
  - [ ] agent_start
  - [ ] agent_end
  - [ ] turn_start
  - [ ] turn_end
  - [ ] message_start
  - [ ] message_update
  - [ ] message_end
  - [ ] tool_execution_start
  - [ ] tool_execution_update
  - [ ] tool_execution_end
  
- [ ] AgentTool
  - [ ] name
  - [ ] label
  - [ ] description
  - [ ] parameters (JSON Schema)
  - [ ] execute()
  
- [ ] AgentToolResult
  - [ ] content
  - [ ] details
  - [ ] isError
  
- [ ] AgentContext
- [ ] AgentLoopConfig
```

#### 6.2 Agent 类

```python
# packages/pi_agent/src/pi_agent/agent.py

# 需要实现的方法
- [ ] __init__(options)
- [ ] 状态管理
  - [ ] set_system_prompt(prompt)
  - [ ] set_model(model)
  - [ ] set_thinking_level(level)
  - [ ] set_tools(tools)
  - [ ] replace_messages(messages)
  - [ ] append_message(message)
  - [ ] clear_messages()
  - [ ] reset()
  
- [ ] 事件订阅
  - [ ] subscribe(callback) -> unsubscribe
  - [ ] _emit_event(event)
  
- [ ] 提示和继续
  - [ ] prompt(input, images)
  - [ ] continue()
  
- [ ] 控制
  - [ ] abort()
  - [ ] wait_for_idle()
  
- [ ] 转向 (Steering)
  - [ ] steer(message)
  - [ ] set_steering_mode(mode)
  - [ ] get_steering_mode()
  - [ ] clear_steering_queue()
  - [ ] _dequeue_steering_messages()
  
- [ ] 跟进 (Follow-up)
  - [ ] follow_up(message)
  - [ ] set_follow_up_mode(mode)
  - [ ] get_follow_up_mode()
  - [ ] clear_follow_up_queue()
  - [ ] _dequeue_follow_up_messages()
  
- [ ] 队列管理
  - [ ] has_queued_messages()
  - [ ] clear_all_queues()
```

#### 6.3 Agent 循环

```python
# packages/pi_agent/src/pi_agent/loop.py

# 需要实现
- [ ] agent_loop(messages, context, config) -> AsyncIterator[AgentEvent]
  - [ ] 消息注入
  - [ ] LLM 调用
  - [ ] 工具执行
  - [ ] 事件发射
  - [ ] 转向检查
  - [ ] 跟进检查
  
- [ ] agent_loop_continue(context, config) -> AsyncIterator[AgentEvent]
  - [ ] 从现有上下文继续
  - [ ] 验证最后一条消息类型
  
- [ ] 工具执行逻辑
  - [ ] 并行执行
  - [ ] 错误处理
  - [ ] 超时处理
  - [ ] 取消支持
  
- [ ] 重试逻辑
  - [ ] API 错误重试
  - [ ] 指数退避
  - [ ] 最大重试次数
```

#### 6.4 消息转换

```python
# 需要实现
- [ ] convert_to_llm(messages: AgentMessage[]) -> Message[]
  - [ ] 过滤非 LLM 消息
  - [ ] 验证消息格式
  
- [ ] transform_context(messages, signal) -> AgentMessage[]
  - [ ] 上下文修剪
  - [ ] 消息压缩
  - [ ] 外部上下文注入
```

#### 测试要求
- [ ] Agent 状态管理测试
- [ ] 事件流测试
- [ ] 工具执行测试
- [ ] 转向测试
- [ ] 跟进测试
- [ ] 错误处理测试
- [ ] 取消测试

---

### Phase 7: pi-agent 工具系统 (3-4 天)

#### 目标
实现完整的工具系统

#### 7.1 工具定义

```python
# 使用 Pydantic 或 JSON Schema
class AgentTool(BaseModel):
    name: str
    label: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable[
        [str, dict, asyncio.Event | None, Callable | None],
        Awaitable[AgentToolResult]
    ]
```

#### 7.2 参数验证

```python
# 需要实现
- [ ] JSON Schema 验证
- [ ] 参数类型转换
- [ ] 默认值处理
- [ ] 必填字段验证
```

#### 7.3 工具执行

```python
# 需要实现
- [ ] 同步/异步执行
- [ ] 超时处理
- [ ] 错误捕获
- [ ] 进度更新 (onUpdate callback)
- [ ] 取消支持 (AbortSignal)
```

#### 7.4 内置工具示例

```python
# packages/pi_agent/src/pi_agent/tools/

- [ ] read_file.py
- [ ] write_file.py
- [ ] edit_file.py
- [ ] bash.py
```

#### 测试要求
- [ ] 参数验证测试
- [ ] 工具执行测试
- [ ] 错误处理测试
- [ ] 超时测试
- [ ] 取消测试

---

### Phase 8: pi-coding-agent CLI (5-7 天)

#### 目标
实现交互式编码代理 CLI

#### 8.1 CLI 框架

```python
# packages/pi_coding_agent/

- [ ] __init__.py
- [ ] cli.py (主入口)
- [ ] __main__.py
```

#### 8.2 运行模式

```python
# 需要实现
- [ ] Interactive 模式 (默认)
  - [ ] REPL 循环
  - [ ] 多行输入
  - [ ] 命令处理
  
- [ ] Print 模式 (-p)
  - [ ] 单次提示
  - [ ] 打印响应
  - [ ] 退出
  
- [ ] JSON 模式 (--mode json)
  - [ ] JSONL 输出
  - [ ] 事件流
  
- [ ] RPC 模式 (--mode rpc)
  - [ ] stdin/stdout 协议
  - [ ] JSON-RPC 格式
```

#### 8.3 内置命令

```python
# 需要实现
- [ ] /help - 帮助
- [ ] /model - 模型选择
- [ ] /tools - 工具管理
- [ ] /clear - 清除上下文
- [ ] /tree - 会话树
- [ ] /resume - 恢复会话
- [ ] /save - 保存会话
- [ ] /load - 加载会话
- [ ] /exit - 退出
```

#### 8.4 会话管理

```python
# 需要实现
- [ ] 会话存储 (JSONL)
- [ ] 会话分支
- [ ] 会话恢复
- [ ] 自动压缩
```

#### 8.5 内置工具

```python
# 需要实现
- [ ] read - 读取文件
- [ ] write - 写入文件
- [ ] edit - 编辑文件
- [ ] bash - 执行命令
```

#### 测试要求
- [ ] CLI 命令测试
- [ ] 各模式测试
- [ ] 会话管理测试
- [ ] 集成测试

---

### Phase 9: 扩展系统 (3-5 天)

#### 目标
实现插件和扩展系统

#### 9.1 Extensions

```python
# 需要实现
- [ ] Extension 协议
- [ ] Extension 加载
- [ ] Extension 注册
- [ ] 工具覆盖
- [ ] 自定义压缩
```

#### 9.2 Skills

```python
# 需要实现
- [ ] Skill 格式 (Markdown)
- [ ] Skill 加载
- [ ] Skill 匹配
- [ ] Skill 执行
```

#### 9.3 Prompt Templates

```python
# 需要实现
- [ ] Template 格式 (Markdown)
- [ ] 变量替换
- [ ] Template 加载
- [ ] Template 执行
```

#### 测试要求
- [ ] Extension 加载测试
- [ ] Skill 匹配测试
- [ ] Template 渲染测试

---

### Phase 10: 文档和示例 (2-3 天)

#### 目标
完善文档和示例

#### 10.1 API 文档

```
docs/
├── api/
│   ├── pi-ai/
│   │   ├── types.md
│   │   ├── stream.md
│   │   ├── providers.md
│   │   └── models.md
│   └── pi-agent/
│       ├── agent.md
│       ├── tools.md
│       └── loop.md
├── guides/
│   ├── getting-started.md
│   ├── providers.md
│   ├── tools.md
│   └── extensions.md
└── examples/
    ├── basic-usage.md
    ├── custom-tools.md
    └── advanced.md
```

#### 10.2 示例完善

```python
examples/
├── 00_quick_start.py          ✓ 已有
├── 01_simple_agent.py          ✓ 已有
├── 02_agent_with_tools.py      ✓ 已有
├── 03_agent_events.py          ✓ 已有
├── 04_steering_followup.py    ✓ 已有
├── 05_streaming_response.py   ✓ 已有
├── 06_provider_config.py       ✓ 已有
├── 07_custom_tools.py          # 新增
├── 08_context_compression.py   # 新增
├── 09_multi_turn.py            # 新增
├── 10_cli_usage.py             # 新增
└── providers_config.py         ✓ 已有
```

---

## 3. 技术栈确认

### 3.1 核心依赖

```toml
[project.dependencies]
python = ">=3.11"
pydantic = ">=2.0,<3"
httpx = ">=0.27,<1"
asyncio = "built-in"

[project.optional-dependencies]
openai = ["openai>=1.50,<2"]
anthropic = ["anthropic>=0.40,<1"]
google = ["google-genai>=1.0,<2"]
all = ["pi-ai[openai,anthropic,google]"]
```

### 3.2 开发依赖

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-mock>=3.14",
    "pytest-cov>=4.0",
    "ruff>=0.8",
    "mypy>=1.0",
    "pyright>=0.1",
]
```

### 3.3 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 包管理 | uv | 现代、快速、支持 workspace |
| 类型验证 | Pydantic v2 | 功能强大、性能好、广泛使用 |
| Schema 验证 | JSON Schema | 标准化、工具支持好 |
| 异步 | asyncio | Python 原生支持 |
| HTTP | httpx | 现代、异步、支持 HTTP/2 |
| 测试 | pytest | 标准、插件丰富 |
| 代码风格 | ruff | 快速、功能全面 |

---

## 4. 里程碑和时间表

### Milestone 1: pi-ai 核心 (Week 1-2)
- Phase 0: 基础设施
- Phase 1: 类型系统
- Phase 2: 事件流

### Milestone 2: pi-ai Provider (Week 3-4)
- Phase 3: Provider 实现
- Phase 4: 模型注册表
- Phase 5: 流式 API

### Milestone 3: pi-agent 核心 (Week 5-6)
- Phase 6: Agent 运行时
- Phase 7: 工具系统

### Milestone 4: pi-coding-agent (Week 7-8)
- Phase 8: CLI 实现
- Phase 9: 扩展系统

### Milestone 5: 文档和发布 (Week 9)
- Phase 10: 文档完善
- 测试覆盖
- 发布准备

---

## 5. 测试策略

### 5.1 单元测试

```python
# 每个 Phase 需要的测试
- [ ] 类型创建测试
- [ ] 验证测试
- [ ] 序列化测试
- [ ] 错误处理测试
```

### 5.2 集成测试

```python
# 需要 Mock 的外部依赖
- [ ] HTTP 响应 Mock
- [ ] API 错误 Mock
- [ ] 文件系统 Mock

# 真实 API 测试
- [ ] OpenAI API 测试
- [ ] Anthropic API 测试
- [ ] Google API 测试
```

### 5.3 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| pi-ai/types | 90% |
| pi-ai/providers | 80% |
| pi-ai/stream | 85% |
| pi-agent/agent | 85% |
| pi-agent/loop | 80% |
| pi-agent/tools | 85% |

---

## 6. 风险和缓解

### 6.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Pydantic v2 不兼容 | 高 | 使用最新版本，参考官方文档 |
| 异步复杂性 | 中 | 充分测试，使用 asyncio 最佳实践 |
| API 变化 | 中 | 监控 API 变化，使用稳定版本 |
| 性能问题 | 中 | 基准测试，优化关键路径 |

### 6.2 项目风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 范围蔓延 | 高 | 严格遵循 Phase，优先核心功能 |
| 时间估计不准 | 中 | 预留缓冲时间，迭代调整 |
| 文档不完整 | 中 | 与开发同步，代码审查 |

---

## 7. 下一步行动

### 立即开始 (本周)
1. [ ] 完善 Phase 0 基础设施
2. [ ] 开始 Phase 1 类型系统
3. [ ] 设置 CI/CD

### 短期 (2 周内)
1. [ ] 完成 pi-ai 核心类型
2. [ ] 实现 OpenAI Provider
3. [ ] 实现基础事件流

### 中期 (1 个月内)
1. [ ] 完成所有主要 Provider
2. [ ] 实现 Agent 核心
3. [ ] 开始 CLI 开发

---

## 8. 附录

### A. 参考资源

- [pi-mono GitHub](https://github.com/badlogic/pi-mono)
- [pi-mono 架构调研](./pi-mono-architecture-research.md)
- [pi-mono Agent 模块调研](./pi-mono-agent-module-research.md)
- [Pydantic v2 文档](https://docs.pydantic.dev/latest/)
- [httpx 文档](https://www.python-httpx.org/)
- [pytest 文档](https://docs.pytest.org/)

### B. 代码风格指南

```python
# 命名约定
- 类名：PascalCase (Agent, AgentTool)
- 函数名：snake_case (stream, complete)
- 常量：UPPER_SNAKE_CASE (KNOWN_APIS)
- 私有：_leading_underscore (_internal_func)

# 类型注解
- 所有公共 API 必须有类型注解
- 使用 typing 模块的现代类型
- 避免使用 Any，使用具体类型或 Protocol

# 文档字符串
- 公共 API 必须有 docstring
- 使用 Google 风格
- 包含示例代码
```

### C. Git 工作流

```bash
# 分支命名
feature/pi-ai-types
feature/pi-agent-loop
fix/anthropic-provider
docs/api-reference

# Commit 消息
feat(pi-ai): add Anthropic provider
fix(pi-agent): handle tool execution errors
docs: update API reference
test: add provider integration tests
```
