# ============================================================
# 🐱 医小喵 · 医疗健康智能问答助手 — Makefile（canonical 入口）
# ============================================================
# 用法：
#   make            # = make test（默认目标）
#   make test       # 运行 pytest 自动化测试
#   make test-fast  # 只跑不依赖模型的测试（无需 Ollama）
#   make start      # 启动服务（需 Ollama 已运行）
#   make ollama     # 启动 Ollama 服务
#   make check      # 环境自检（Python/依赖/Ollama/模型/知识库）
#   make clean      # 清理缓存
# ============================================================
SHELL := /bin/bash
VENV  ?= $(HOME)/medqa-venv
PY    ?= $(VENV)/bin/python
OLLAMA_HOST ?= 127.0.0.1:11434

.DEFAULT_GOAL := test
.PHONY: test test-fast start ollama check clean help

## test: 运行完整 pytest 测试（需 Ollama 运行）
test:
	@echo "▶ pytest（完整，需 Ollama）"
	@$(PY) -m pytest tests/test_api.py -q --tb=short

## test-fast: 只跑不依赖大模型的测试（无需 Ollama）
test-fast:
	@echo "▶ pytest（跳过需 Ollama 的用例）"
	@$(PY) -m pytest tests/test_api.py -q --tb=short \
		-k "not chat" || true

## ollama: 启动 Ollama 服务（后台）
ollama:
	@if curl -sf -m 3 http://$(OLLAMA_HOST)/api/tags >/dev/null 2>&1; then \
		echo "  ✓ Ollama 已在运行"; \
	else \
		echo "  启动 ollama serve …"; \
		nohup ollama serve > /tmp/ollama.log 2>&1 & \
		sleep 5; \
		curl -sf -m 5 http://$(OLLAMA_HOST)/api/tags >/dev/null && echo "  ✓ 已就绪" || echo "  ✗ 启动失败，见 /tmp/ollama.log"; \
	fi

## start: 启动医小喵服务
start:
	@bash start.sh

## check: 环境自检
check:
	@echo "▶ 环境自检"
	@echo -n "  虚拟环境: "; [ -x "$(PY)" ] && echo "$(VENV) ✓" || echo "缺失 ✗"
	@echo -n "  依赖: "; $(PY) -c "import fastapi, pytest, ollama, chromadb; print('✓')" 2>/dev/null || echo "缺失 ✗"
	@echo -n "  Ollama 服务: "; curl -sf -m 3 http://$(OLLAMA_HOST)/api/tags >/dev/null && echo "运行中 ✓" || echo "未运行 ✗（make ollama）"
	@echo -n "  知识库: "; [ -d "data/chroma" ] || [ -d "data/kb" ] && echo "存在 ✓" || echo "未构建（python build_kb.py）"

## clean: 清理 Python 缓存
clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@rm -rf .pytest_cache
	@echo "已清理：__pycache__ / *.pyc / .pytest_cache"

## help: 显示可用命令
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
