FROM langchain/langgraph-api:3.13

# 安装 Node.js + npm (用于 MCP stdio 工具的 npx)
# langgraph-api:3.13 默认使用 Wolfi Linux，包管理器为 apk
RUN apk add --no-cache nodejs npm

# 修复 OpenSSL 3.x 兼容性：允许 mem0 等库使用传统哈希算法
ENV OPENSSL_CONF=/dev/null

# 复制项目文件（langgraph-api 工作目录为 /deps）
COPY . /deps

# 安装 Python 依赖
RUN cd /deps && pip install --no-cache-dir -e .
