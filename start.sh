#!/bin/bash
# ============================================
# 🐱 医小喵 · 一键启动脚本（环节⑧ 部署）
# 用法: bash start.sh
# 自动: 检查/启动 Ollama → 检查模型 → 启动 API → 打印访问地址
# ============================================
export PATH=$PATH:$HOME/.local/bin
BASE="/mnt/d/Project/JXprojiect/医疗健康智能问答助手"

echo "🐾 医小喵启动中喵~"

# 1. Ollama 服务
if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "✅ Ollama 已在运行"
else
  echo "🔥 启动 Ollama ..."
  nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
  for i in $(seq 1 15); do
    if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
      echo "✅ Ollama 就绪 (${i}s)"
      break
    fi
    sleep 1
  done
fi

# 2. 模型检查
if ! ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
  echo "⚠️ 未找到 qwen2.5:7b 模型！请先执行: ollama pull qwen2.5:7b"
fi
if ! ollama list 2>/dev/null | grep -q "qwen3-embedding"; then
  echo "⚠️ 未找到 embedding 模型！请先执行: ollama pull qwen3-embedding:0.6b"
fi

# 3. API 服务
if curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
  echo "✅ API 已在运行 http://localhost:8000"
else
  echo "🚀 启动 API 服务 ..."
  cd "$BASE" || exit 1
  nohup bash -c "source ~/medqa-venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000" \
    > /tmp/yixiaomiao_api.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
      echo "✅ API 就绪 (${i}s)"
      break
    fi
    sleep 1
  done
fi

echo ""
echo "🎉 医小喵启动完成！浏览器打开: http://localhost:8000 喵~"
echo "   （局域网内其他人可用 http://<本机IP>:8000 访问）"
