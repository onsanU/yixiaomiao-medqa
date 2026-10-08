#!/bin/bash
# ============================================
# 🐱 咪咪一键启动 Ollama + Qwen 大厨
# 用法: bash start_ollama.sh
# ============================================
export PATH=$PATH:$HOME/.local/bin

echo "🐾 咪咪来啦，检查 Ollama 状态喵~"

# 1. 检查是否已在运行
if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "✅ Ollama 已经在运行啦 (localhost:11434)，直接开工！"
else
  echo "🔥 正在启动 Ollama ..."
  nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
  # 等待服务就绪（最多等15秒）
  for i in $(seq 1 15); do
    if curl -s --max-time 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
      echo "✅ 服务就绪！(第 ${i} 秒)"
      break
    fi
    sleep 1
  done
fi

# 2. 检查模型在不在
echo ""
echo "📦 模型列表："
ollama list

# 3. 快速测试：让 Qwen 大厨炒一道小菜
echo ""
echo "🧪 快速测试中..."
curl -s --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"qwen3.5:4b","prompt":"你好！用一句话介绍一下自己。","stream":false}' \
  | python3 -c "import json,sys; print('🐱 Qwen 大厨说:', json.load(sys.stdin).get('response','')[:150])"

echo ""
echo "🎉 全部就绪！主人可以开始干活啦喵~ (=^･ω･^=)"
