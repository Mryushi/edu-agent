# Edu Agent

AI 驱动的教育辅导智能体平台，支持多模型对话、文档解析、RAG 知识库和长期记忆。

## 项目结构

| 目录 | 说明 | 技术栈 |
|------|------|--------|
| [edu-agent/](edu-agent/) | AI 教育辅导 agent 后端 | Python 3.13+, LangGraph, Milvus, mem0 |
| [agent-ui/](agent-ui/) | Web 聊天交互界面 | Next.js 16, React 19, Tailwind（基于 [Deep Agents UI](https://github.com/langchain-ai/deep-agents-ui)） |

## 快速开始

### 1. 启动后端

```bash
cd edu-agent
cp .env.example .env   # 编辑填入 API Key
uv sync

# 开发模式（支持热重载，默认 localhost:2026）
langgraph dev

# 生产模式（默认仅监听 localhost，外部无法访问）
langgraph up

# 生产模式（允许外部访问，绑定 0.0.0.0）
langgraph up --host 0.0.0.0
```

服务默认运行在 http://localhost:2026

### 2. 启动前端

```bash
cd agent-ui
yarn install
yarn dev               # 默认 http://localhost:3000
```

在设置中填入后端地址和 Assistant ID 即可使用。

## 核心特性

- **动态模型选择** — 文本用 DeepSeek，图片自动切换 Doubao Vision
- **RAG 知识库** — Milvus 向量存储，支持增量入库、BM25 混合搜索、中文分词
- **长期记忆** — mem0 驱动的学生画像，记录偏好、进度、目标
- **统一嵌入模型** — RAG 和 mem0 共用嵌入配置，支持 Ollama 和 OpenAI 兼容接口
- **文件解析** — 统一解析 PDF/DOCX/TXT，自动分段缓存，大文件提示入库
- **MCP 工具扩展** — 通过 MCP 协议接入外部工具
- **虚拟文件系统** — Agent 文件操作沙箱化，安全隔离

## 配置说明

### 嵌入模型配置（RAG 和 mem0 共用）

```bash
# 嵌入模型提供商：ollama 或 openai
EMBEDDING_PROVIDER=ollama

# Ollama 嵌入配置
EMBEDDING_MODEL=qwen3-embedding:0.6b
EMBEDDING_DIMS=1024
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI 兼容接口配置（当 EMBEDDING_PROVIDER=openai 时使用）
OPENAI_EMBEDDING_API_KEY=your_api_key
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
```

### 其他配置

参见 [edu-agent/.env.example](edu-agent/.env.example) 获取完整配置项说明。

## 架构概览

```
edu-agent/
├── src/app/
│   ├── agents/          # Agent 定义和工具注册
│   ├── middleware/       # 中间件（PDF 上下文注入等）
│   ├── services/        # 业务逻辑层
│   ├── repositories/    # 数据访问层
│   ├── tools/           # 工具模块（文件解析、分块等）
│   ├── core/            # 配置和模型工厂
│   └── workspace/       # 运行时文件存储
└── start_server.py      # 服务启动脚本
```

## 许可证

MIT
