#!/bin/sh
# 运行时注入 NEXT_PUBLIC_* 环境变量到 Next.js 客户端代码
# Next.js standalone 模式下，NEXT_PUBLIC_* 在构建时被替换，需要在运行时重新注入

if [ -n "$NEXT_PUBLIC_LANGGRAPH_API_URL" ]; then
  echo "注入 NEXT_PUBLIC_LANGGRAPH_API_URL=$NEXT_PUBLIC_LANGGRAPH_API_URL"
  # 替换所有 JS 文件中的占位符
  find /app/.next/static /app/.next/standalone -type f -name "*.js" -exec \
    sed -i "s|http://localhost:8123|$NEXT_PUBLIC_LANGGRAPH_API_URL|g" {} + 2>/dev/null || true
fi

exec "$@"
