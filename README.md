# Edu Agent

AI 驱动的教育辅导智能体平台，支持多模型对话、文档解析、RAG 知识库和长期记忆。

## 项目结构

| 目录 | 说明 | 技术栈 |
|------|------|--------|
| [edu-agent/](edu-agent/) | AI 教育辅导 agent 后端 | Python 3.13+, LangGraph, Milvus, mem0 |
| [agent-ui/](agent-ui/) | Web 聊天交互界面 | Next.js 16, React 19, Tailwind |
| llm_wiki/ | 桌面知识管理 + AI 对话 | Tauri v2, React, Vite |

## 快速开始

### 1. 启动后端

```bash
cd edu-agent
cp .env.example .env   # 编辑填入 API Key
uv sync
python start_server.py  # 默认 http://localhost:2026
```

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
- **文件解析** — 统一解析 PDF/DOCX/TXT，自动分段缓存
- **MCP 工具扩展** — 通过 MCP 协议接入外部工具
- **虚拟文件系统** — Agent 文件操作沙箱化，安全隔离

## 配置

参见 [edu-agent/.env.example](edu-agent/.env.example) 获取完整配置项说明。
