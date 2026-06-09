# Edu Agent

AI 驱动的教育辅导智能体平台，支持多模型对话、文档解析、RAG 知识库和长期记忆。

## 项目结构

| 目录 | 说明 | 技术栈 |
|------|------|--------|
| [edu-agent/](edu-agent/) | AI 教育辅导 agent 后端 | Python 3.13+, LangGraph, Milvus, mem0 |
| [agent-ui/](agent-ui/) | Web 聊天交互界面 | Next.js 16, React 19, Tailwind（基于 [Deep Agents UI](https://github.com/langchain-ai/deep-agents-ui)） |

## 环境准备

### Milvus 向量数据库

项目依赖 Milvus 存储 RAG 知识库和 mem0 长期记忆。Windows 环境推荐使用 Docker Desktop：

**前置条件**：安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)，并启用 WSL 2 后端，内存建议分配 4GB+。

```bash
# 下载官方 Docker Compose 文件
mkdir milvus && cd milvus
curl -o docker-compose.yml https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed/docker-compose.yml

# 启动 Milvus Standalone
docker compose up -d

# 验证运行状态
docker compose ps
```

启动后可通过 [Attu](https://github.com/zilliztech/attu) Web UI 管理：

```bash
docker run -d -p 8000:3000 -e MILVUS_URL=host.docker.internal:19530 zilliz/attu:latest
```

> 默认端口：`19530`（gRPC）、`9091`（指标）。详细文档见 [Milvus Windows 安装指南](https://milvus.io/docs/zh/install_standalone-windows.md)。

### Ollama（可选，用于本地嵌入）

若使用 Ollama 作为嵌入模型提供商：

```bash
# 安装 Ollama 后拉取嵌入模型
ollama pull nomic-embed-text
```

## 快速开始

### 1. 启动后端

```bash
cd edu-agent
cp .env.example .env   # 编辑填入 API Key
uv sync

# 开发模式（支持热重载，默认 localhost:2026）
langgraph dev
```

服务默认运行在 http://localhost:2026

### 2. 启动前端

```bash
cd agent-ui
yarn install
yarn dev               # 默认 http://localhost:3000
```

在设置中填入后端地址和 Assistant ID 即可使用。

### 3. Docker 部署（可选）

使用 `langgraph up` 可将后端打包为 Docker 容器运行，适合生产环境部署。

```bash
cd edu-agent
cp .env.example .env   # 编辑填入 API Key

# 构建镜像并启动容器
langgraph up
```

**网络配置**：容器内的 `localhost` 指向容器自身，若 Milvus、Ollama 等服务运行在宿主机上，需修改 `.env`：

```env
MILVUS_URL=http://host.docker.internal:19530
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Dockerfile 说明**（[edu-agent/Dockerfile](edu-agent/Dockerfile)）：
- 基础镜像：`langchain/langgraph-api:3.13`（Wolfi Linux）
- 安装 Node.js/npm（供 MCP stdio 工具使用）
- 安装 spaCy 及英文模型
- 修复 OpenSSL 3.x 兼容性（mem0 等库的传统哈希算法）

**常用命令**：

```bash
langgraph up          # 启动容器（后台运行）
langgraph down        # 停止并移除容器
langgraph logs        # 查看容器日志
```

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
OLLAMA_BASE_URL=http://localhost:11434       # Docker 部署时改为 host.docker.internal

# OpenAI 兼容接口配置（当 EMBEDDING_PROVIDER=openai 时使用）
OPENAI_EMBEDDING_API_KEY=your_api_key
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMS=1536
```

### 其他配置

参见 [edu-agent/.env.example](edu-agent/.env.example) 获取完整配置项说明。