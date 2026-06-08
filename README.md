# SweepMind 扫地机器人智能客服 🤖

> 基于 LangChain ReAct Agent + MCP + RAG + Streamlit 的扫地机器人智能客服系统

---

## 项目简介

**SweepMind 扫地机器人智能客服**是一款面向扫地机器人/扫拖一体机器人用户的 AI 智能体应用。系统支持两种工具调用模式：

- **MCP 模式**：工具以 MCP（Model Context Protocol）服务的形式独立运行，Agent 通过 MCP 协议与工具服务通信，符合 Anthropic 推出的开放标准。
- **传统模式**：工具以 LangChain `@tool` 装饰器定义，Agent 通过 Function Calling 直接调用。

两种模式通过配置文件 `config/agent.yml` 中的 `use_mcp` 开关切换，前端无需任何改动。

### 核心能力一览

| 能力 | 说明 |
|------|------|
| RAG 增强检索 | 将产品手册、常见问题、维护指南等文档向量化存储，回答时优先检索知识库 |
| 和风天气查询 | 通过 LLM 提取城市信息，调用和风天气 API 获取实时天气 |
| 使用报告生成 | 中间件检测报告意图后自动切换提示词，结合外部 CSV 数据生成 Markdown 报告 |
| 多轮工具调用 | Agent 自主规划并多轮调用工具，直至满足用户需求 |
| 流式响应 | 最终结果在网页端逐字流式呈现 |
| 完善日志 | 按天分文件，同时输出到控制台与文件 |

---

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| LLM | Ollama + `qwen3:4b` | 本地部署的对话大模型 |
| Embedding | Ollama + `bge-large` | 文本向量化模型 |
| Agent 框架 | LangChain + LangGraph | ReAct 推理与图执行引擎 |
| 工具协议 | MCP（Model Context Protocol） | Anthropic 推出的标准化工具通信协议 |
| MCP 适配 | `langchain-mcp-adapters` | MCP 工具到 LangChain 工具的桥接层 |
| MCP SDK | `mcp` | MCP 服务端/客户端 Python SDK |
| 向量数据库 | Chroma | 本地持久化向量存储 |
| 前端 | Streamlit | 轻量级 Web 界面 |
| 外部服务 | 和风天气 API | 天气数据源 |
| 语言 | Python 3.10+ | 类型注解使用 3.10 语法 |

---

## 系统架构

### MCP 模式架构（默认）

```
┌─────────────────────────────────────────────────────┐
│              Streamlit 前端 (app.py)                  │
│   对话历史 | 流式显示 | 会话状态管理                      │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│         MCPReactAgent (agent/mcp_react_agent.py)     │
│  ┌────────────────────────────────────────────────┐ │
│  │  MCPMiddlewareManager (agent/mcp_middleware.py) │ │
│  │  ├─ on_tool_call    工具调用监控与日志            │ │
│  │  ├─ on_before_model 模型调用前日志               │ │
│  │  └─ get_system_prompt  动态提示词切换            │ │
│  └────────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────────┐ │
│  │  MultiServerMCPClient                          │ │
│  │  ← stdio 传输 → MCP Server 子进程              │ │
│  └────────────────────────────────────────────────┘│
└──────────────────────┬──────────────────────────────┘
                       │ MCP 协议 (stdio)
┌──────────────────────▼──────────────────────────────┐
│         MCP Server (agent/mcp/server.py)                │
│  FastMCP("zhisaotong-tools")                        │
│  工具集:                                             │
│  ├─ rag_summarize       RAG 知识库检索               │
│  ├─ get_weather          和风天气查询                 │
│  ├─ get_user_id          获取用户 ID                 │
│  ├─ get_current_month    获取当前月份                 │
│  ├─ fetch_external_data  获取外部使用记录             │
│  └─ fill_context_for_report  报告模式信号             │
└──┬──────────────┬───────────────┬───────────────────┘
   │              │               │
   ▼              ▼               ▼
┌──────────┐ ┌─────────────┐ ┌────────────────┐
│ RAG 服务 │ │  和风 API   │ │  外部 CSV 数据 │
│ (rag/)   │ │  (天气)     │ │ data/external/ │
└────┬─────┘ └─────────────┘ └────────────────┘
     │
┌────▼─────────────────────────────┐
│  tool_impl.py（业务逻辑层）       │
│  两种模式共享的纯函数实现          │
│  query_weather / query_rag / ... │
└────┬─────────────────────────────┘
     │
┌────▼─────────────────────────────┐
│  Chroma 向量数据库 (chroma_db/)   │
│  Embedding: bge-large            │
│  知识库文档 (data/)               │
└──────────────────────────────────┘
```

### 双模式切换机制

```
config/agent.yml
    │
    ├── use_mcp: true  ──→  agent/mcp/mcp_react_agent.py
    │                        ├─ 后台守护线程运行 asyncio 事件循环
    │                        ├─ MultiServerMCPClient 连接 MCP Server
    │                        ├─ create_react_agent(prompt=动态回调)
    │                        └─ astream 异步流式执行
    │
    └── use_mcp: false ──→  agent/traditional/react_agent.py
                             ├─ create_agent(tools=[...], middleware=[...])
                             └─ stream 同步流式执行
```

---

## 目录结构

```
Agent/
├── app.py                          # Streamlit 前端入口（双模式切换）
│
├── agent/
│   ├── tools/
│   │   └── tool_impl.py            # 工具业务逻辑（纯函数，两种模式共享）
│   │
│   ├── traditional/                # 传统模式（Function Calling）
│   │   ├── react_agent.py          # Agent 入口
│   │   ├── tools.py                # @tool 注册壳 → tool_impl
│   │   └── middleware.py           # 中间件（@wrap_tool_call 等）
│   │
│   └── mcp/                        # MCP 模式
│       ├── mcp_react_agent.py      # Agent 入口
│       ├── mcp_client.py           # MCP 客户端连接工具
│       ├── mcp_middleware.py       # 中间件管理器
│       ├── server.py               # MCP 服务端（FastMCP，暴露 6 个工具）
│       └── __init__.py
│
├── rag/
│   ├── rag_service.py              # RAG 检索摘要服务
│   └── vector_store.py             # Chroma 向量库管理
│
├── model/
│   └── factory.py                  # 模型工厂（ChatOllama + OllamaEmbeddings）
│
├── utils/
│   ├── config_handler.py           # YAML 配置加载器
│   ├── logger_handler.py           # 日志工具（控制台 + 按天文件）
│   ├── prompt_loader.py            # 提示词文件加载器
│   ├── file_handler.py             # 文档加载（PDF/TXT）、MD5 哈希
│   ├── path_tool.py                # 绝对路径工具
│   └── qweather.py                 # 和风天气 API 工具函数
│
├── config/
│   ├── agent.yml                   # Agent 配置（MCP 开关、和风 API、外部数据路径）
│   ├── rag.yml                     # 模型名称配置
│   ├── chroma.yml                  # 向量库配置
│   └── prompts.yml                 # 提示词文件路径映射
│
├── prompts/
│   ├── main_prompt.txt             # 主 ReAct 系统提示词
│   ├── report_prompt.txt           # 报告生成提示词
│   ├── rag_summarize.txt           # RAG 摘要提示词
│   └── location_extract_prompt.txt # 城市信息抽取提示词
│
├── data/
│   ├── 扫地机器人100问.pdf
│   ├── 扫地机器人100问2.txt
│   ├── 扫拖一体机器人100问.txt
│   ├── 故障排除.txt
│   ├── 维护保养.txt
│   ├── 选购指南.txt
│   └── external/
│       └── records.csv             # 用户使用记录数据
│
├── chroma_db/                      # Chroma 持久化目录（自动生成）
├── logs/                           # 日志文件目录（自动生成）
├── md5.text                        # 文档 MD5 去重记录
│
├── test_mcp_server.py              # MCP 服务端独立测试
├── test_mcp_agent.py               # MCP Agent 端到端测试
├── requirements.txt                # Python 依赖清单
└── README.md                       # 项目文档
```

---

## MCP 协议说明

### 什么是 MCP

MCP（Model Context Protocol）是 Anthropic 推出的开放标准协议，用于规范 LLM 应用与外部工具之间的通信。与传统 Function Calling 的核心区别：

| 对比项 | Function Calling | MCP |
|--------|-----------------|-----|
| 协议 | LLM 原生能力，各厂商格式不统一 | JSON-RPC 2.0，开放标准 |
| 工具注册 | 在 prompt/schema 中定义 | MCP Server 暴露 tools/resources |
| 通信方式 | Agent 进程内部直接调用 | Client 与 Server 跨进程通信（stdio/SSE/HTTP） |
| 可复用性 | 工具绑定在特定 Agent 代码中 | MCP Server 可被任何 MCP Client 调用 |

### 本项目的 MCP 实现

- **业务逻辑层**（`agent/tools/tool_impl.py`）：所有工具的核心逻辑以纯函数实现（`query_weather`、`query_rag` 等），传统模式和 MCP 模式共享同一份代码，修改逻辑只需改一处。
- **传统模式**（`agent/traditional/`）：`@tool` 薄壳注册，内部调用 `tool_impl.py`。
- **MCP Server**（`agent/mcp/server.py`）：`@mcp_server.tool()` 薄壳注册，内部调用 `tool_impl.py`，通过 **stdio** 传输运行。
- **MCP Client**（`agent/mcp/mcp_react_agent.py`）：使用 `MultiServerMCPClient` 连接 Server，将 MCP 工具转换为 LangChain 工具供 Agent 使用。
- **信号机制**：`fill_context_for_report` 工具返回 `{"__mcp_signal__": "report_mode"}` JSON 标记，客户端中间件检测后触发提示词切换。

---

## 配置说明

### 1. MCP 模式开关

编辑 `config/agent.yml`：

```yaml
# true: 使用 MCP 协议（工具运行在独立子进程中）
# false: 使用传统 Function Calling（工具在主进程中直接调用）
use_mcp: true
```

### 2. 和风天气 API

编辑 `config/agent.yml`，替换为你自己的 API Host 和 Key：

```yaml
qweather_api_host: your_qweather_api_host
qweather_api_key: your_qweather_api_key
qweather_timeout: 5
qweather_lang: zh
qweather_range: cn
```

> 可在 [和风天气开放平台](https://console.qweather.com/) 申请 Web 服务类型的 API Key 和 API Host。

### 3. 模型配置

编辑 `config/rag.yml`：

```yaml
chat_model_name: qwen3:4b         # 对话大模型（需通过 ollama pull 预下载）
embedding_model_name: bge-large:latest  # 向量化模型
```

### 4. 向量库配置

编辑 `config/chroma.yml`：

```yaml
collection_name: agent
persist_directory: ./chroma_db
k: 3                    # 检索返回的最相关文档数量
chunk_size: 200         # 文本分块大小
chunk_overlap: 20       # 分块重叠长度
data_path: ./data
allow_knowledge_file_type: ["txt", "pdf"]
```

### 5. 提示词配置

编辑 `config/prompts.yml` 可自定义各提示词文件路径：

```yaml
main_prompt_path: prompts/main_prompt.txt
rag_summarize_prompt_path: prompts/rag_summarize.txt
report_prompt_path: prompts/report_prompt.txt
location_extract_prompt_path: prompts/location_extract_prompt.txt
```

---

## 快速开始

### 1. 环境准备

- Python 3.10+
- [Ollama](https://ollama.com/) 已安装并运行

```bash
# 下载所需模型
ollama pull qwen3:4b
ollama pull bge-large:latest
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
cp config/agent.yml.example config/agent.yml
```
编辑 `config/agent.yml`，填入和风天气的 `qweather_api_host` 和 `qweather_api_key`。

### 4. 启动应用

```bash
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，即可开始对话。

---

## 使用方式

### 产品咨询

直接提问扫地机器人的使用、维护、故障排除等问题，Agent 从知识库检索后回答：

```
用户：扫地机器人的滤网多久需要更换一次？
用户：扫拖一体机器人和扫地机器人有什么区别？
用户：扫地机器人吸力变弱了怎么办？
```

### 天气查询

Agent 自动提取城市信息，调用和风天气 API 返回实时天气：

```
用户：北京今天的天气怎么样？
用户：杭州适合用扫地机器人吗？
```

### 使用报告生成

Agent 检测到报告意图后，自动切换提示词并调用外部数据生成报告：

```
用户：帮我生成我的使用报告
用户：给我一份扫地机器人的使用分析和保养建议
```

---

## 工具列表

| 工具 | 描述 | 业务逻辑 | MCP 注册 | 传统注册 |
|------|------|:--------:|:--------:|:--------:|
| `rag_summarize` | 从向量知识库检索参考资料 | `tool_impl.py` | `agent/mcp/server.py` | `agent/traditional/tools.py` |
| `get_weather` | 提取城市并查询实时天气 | `tool_impl.py` | `agent/mcp/server.py` | `agent/traditional/tools.py` |
| `get_user_id` | 获取当前用户 ID | `tool_impl.py` | `agent/mcp/server.py` | `agent/traditional/tools.py` |
| `get_current_month` | 获取当前月份 | `tool_impl.py` | `agent/mcp/server.py` | `agent/traditional/tools.py` |
| `fetch_external_data` | 获取指定用户指定月份的使用记录 | `tool_impl.py` | `agent/mcp/server.py` | `agent/traditional/tools.py` |
| `fill_context_for_report` | 触发报告模式信号 | — | `agent/mcp/server.py` | `agent/traditional/tools.py` |

---

## 中间件机制

### MCP 模式中间件（`agent/mcp/mcp_middleware.py`）

```
MCPMiddlewareManager
  ├─ on_tool_call()        记录工具名称、参数、成功/失败状态
  │                        检测 fill_context_for_report 的信号标记
  │                        将 report_mode 置为 True
  │
  ├─ on_before_model()     记录当前消息数量及最新消息内容
  │
  └─ get_system_prompt()   report_mode == True  → 报告生成提示词
                           report_mode == False → 主 ReAct 提示词
```

### 传统模式中间件（`agent/traditional/middleware.py`）

```
monitor_tool         (@wrap_tool_call)  工具调用监控，设置 context["report"]
log_before_model     (@before_model)    模型调用前日志
report_prompt_switch (@dynamic_prompt)  根据 context["report"] 动态切换提示词
```

### 动态提示词切换流程

```
用户："帮我生成使用报告"
  │
  ▼
Agent 思考：需要调用 fill_context_for_report
  │
  ▼
fill_context_for_report 执行
  ├─ MCP 模式：返回 {"__mcp_signal__": "report_mode"}
  │             客户端中间件检测到标记 → report_mode = True
  │
  └─ 传统模式：中间件设置 runtime.context["report"] = True
  │
  ▼
dynamic_prompt 回调触发
  ├─ report_mode == True → 返回 report_prompt.txt
  └─ 下一次 LLM 调用使用报告生成提示词
  │
  ▼
Agent 使用报告提示词 + 工具数据生成 Markdown 报告
```

---

## 测试

### MCP Server 独立测试

验证 MCP 服务端能否正常启动、暴露工具、并响应调用：

```bash
python test_mcp_server.py
```

预期输出：

```
正在启动 MCP Server ...
MCP Server 连接成功!

可用工具 (6): ['get_weather', 'rag_summarize', 'get_user_id', 'get_current_month', 'fetch_external_data', 'fill_context_for_report']

[get_user_id] => 1003
[get_current_month] => 2025-06
[fill_context_for_report] => {"__mcp_signal__": "report_mode"}
[rag_summarize] => ...
[fetch_external_data] => {'特征': '...', '效率': '...', ...}

所有工具测试通过!
```

### MCP Agent 端到端测试

验证三种典型场景（产品咨询、天气查询、报告生成）：

```bash
python test_mcp_agent.py
```

---

## 日志说明

日志文件存放在 `logs/` 目录下，按天自动创建：

```
logs/
└── agent_20250607.log    # 格式：{name}_{YYYYMMDD}.log
```

日志格式：
```
2025-06-07 12:00:00,123 - agent - INFO - mcp_middleware.py:16 - [tool monitor]执行工具：rag_summarize
```

- **控制台**：INFO 及以上
- **文件**：DEBUG 及以上（更详细）

---

## 知识库

知识库文档存放在 `data/` 目录，支持 `.txt` 和 `.pdf`。首次启动自动向量化存入 Chroma，已处理文档通过 MD5 哈希去重。

| 文件 | 内容 |
|------|------|
| `扫地机器人100问.pdf` | 常见问题解答（PDF） |
| `扫地机器人100问2.txt` | 补充问答 |
| `扫拖一体机器人100问.txt` | 扫拖一体机常见问题 |
| `故障排除.txt` | 故障排除指南 |
| `维护保养.txt` | 日常维护保养说明 |
| `选购指南.txt` | 购买建议与选型指南 |

### 扩展知识库

1. 将新的 `.txt` 或 `.pdf` 文件放入 `data/` 目录
2. 确认文件编码为 UTF-8（`.txt` 文件），否则加载时可能乱码
3. 运行向量库构建脚本，将新文档向量化入库：

```bash
python rag/vector_store.py
```

脚本会自动扫描 `data/` 下所有 `.txt` 和 `.pdf` 文件，通过 MD5 哈希跳过已入库的文档，只处理新增文件。处理完成后控制台会输出加载成功的日志。

> 如果需要删除已有知识库重新构建，可直接删除 `chroma_db/` 目录和 `md5.text` 文件，再重新运行脚本。

### 调整检索参数

编辑 `config/chroma.yml` 可优化检索效果：

```yaml
k: 3              # 返回最相关的文档数量，增大可提高召回率但增加上下文长度
chunk_size: 200   # 文本分块大小（字符数），过小会丢失上下文，过大会降低精度
chunk_overlap: 20 # 相邻分块的重叠字符数，避免语义截断
```

---

## 和风天气调用流程

```
用户提问（如"杭州今天天气怎么样"）
        │
        ▼
LLM 提取城市名称（调用 location_extract_prompt）
        │
        ▼
GeoAPI 城市搜索 → 获取 LocationID
/geo/v2/city/lookup (location, key)
        │
        ▼
天气 API 查询实时天气
/v7/weather/now (LocationID, key)
        │
        ▼
解析 JSON 响应 → 返回格式化天气信息
```

---

## 后续优化方向

- 将向量数据库从 Chroma 替换为 Redis（更适合生产部署）
- 增加用户身份认证与多用户会话隔离
- 支持更多文档格式（Word、Excel 等）
- MCP Server 拆分为多个独立服务（天气服务、RAG 服务、数据服务）
- 将 MCP Server 的 stdio 传输升级为 SSE/HTTP，支持远程部署

---

## 许可证

本项目仅供学习与参考使用。
