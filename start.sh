#!/bin/bash
# ============================================
# 🐱 医小喵 · 一键启动脚本（环节⑧ 部署）
# 用法: bash start.sh
# 自动: 检查/启动 Ollama → 检查模型 → 启动 API → 打印访问地址
# ============================================
export PATH=$PATH:$HOME/.local/bin
BASE="/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa"

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
if ! ollama list 2>/dev/null | grep -q "qwen3.5:4b"; then
  echo "⚠️ 未找到 qwen3.5:4b 模型！请先执行: ollama pull qwen3.5:4b"
fi
if ! ollama list 2>/dev/null | grep -q "qwen3-embedding"; then
  echo "⚠️ 未找到 embedding 模型！请先执行: ollama pull qwen3-embedding:0.6b"
fi

# 3. SenseVoice ASR 服务（🎤 语音输入，2026-09-03 新增）
if curl -s --max-time 2 http://127.0.0.1:8002/health > /dev/null 2>&1; then
  echo "✅ ASR 服务已在运行 (127.0.0.1:8002)"
else
  echo "🎧 启动 SenseVoice ASR 服务 ..."
  cd "$BASE" || exit 1
  nohup bash -c "~/sensevoice-venv/bin/uvicorn app.asr_server:app --host 127.0.0.1 --port 8002" \
    > /tmp/yixiaomiao_asr.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -s --max-time 2 http://127.0.0.1:8002/health > /dev/null 2>&1; then
      echo "✅ ASR 就绪 (${i}s)"
      break
    fi
    sleep 1
  done
fi

# 4. API 服务
if curl -s --max-time 2 http://localhost:8001/health > /dev/null 2>&1; then
  echo "✅ API 已在运行 http://localhost:8001"
else
  echo "🚀 启动 API 服务 ..."
  cd "$BASE" || exit 1
  nohup bash -c "source ~/medqa-venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8001" \
    > /tmp/yixiaomiao_api.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -s --max-time 2 http://localhost:8001/health > /dev/null 2>&1; then
      echo "✅ API 就绪 (${i}s)"
      break
    fi
    sleep 1
  done
fi

# 5. Cloudflare 公网隧道（正式域名 yixiaomiao.osanu.dpdns.org，2026-09-08 新增）
#    隧道云端 ingress: yixiaomiao.osanu.dpdns.org → localhost:8001
#    （2026-09-26 医小喵从 8000 改到 8001，让出 8000 给皮肤癌项目；同一隧道挂两个子域名）
CF_TOKEN_FILE="$HOME/.cloudflared/yixiaomiao-run.token"
if [ -f "$CF_TOKEN_FILE" ]; then
  if pgrep -f "cloudflared tunnel run" > /dev/null 2>&1; then
    echo "✅ 公网隧道已在运行 https://yixiaomiao.osanu.dpdns.org"
  else
    echo "🌐 启动 Cloudflare 公网隧道 ..."
    # setsid 真正脱离会话：nohup 只防 SIGHUP，setsid 防父进程/终端退出
    setsid nohup bash -c "cloudflared tunnel run --token-file $CF_TOKEN_FILE" \
      > /tmp/yixiaomiao_cf.log 2>&1 < /dev/null &
    disown 2>/dev/null || true
    for i in $(seq 1 20); do
      if curl -s --max-time 5 -o /dev/null -w "%{http_code}" https://yixiaomiao.osanu.dpdns.org/health 2>/dev/null | grep -q "200"; then
        echo "✅ 公网隧道就绪 (${i}s)"
        break
      fi
      sleep 1
    done
  fi
fi

echo ""
echo "🎉 医小喵启动完成！浏览器打开: http://localhost:8001 喵~"
echo "   （局域网内其他人可用 http://<本机IP>:8001 访问）"
echo "   （公网固定地址 https://yixiaomiao.osanu.dpdns.org ，电脑别关机喵）"
