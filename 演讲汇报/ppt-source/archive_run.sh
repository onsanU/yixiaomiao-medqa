#!/usr/bin/env bash
# 生成 compare_4way.py 的真实输出存档（现场演示兜底用）
set -euo pipefail
OUT="/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/演讲汇报/演示输出存档_compare4way.txt"
cd /home/wpc15/medical-ft
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

{
  echo "================================================================"
  echo " 演示输出存档 · compare_4way.py"
  echo " 内容：原版 qwen3.5:4b  vs  +3000档LoRA  vs  +5000档LoRA(续训) 同答 3 道医疗题"
  echo " 生成时间：$(date '+%Y-%m-%d %H:%M:%S')"
  echo " 运行环境：WSL Ubuntu · shixun-venv (torch 2.11+cu128) · RTX 5070 Laptop 8G"
  echo " 运行命令：cd ~/medical-ft && ~/shixun-venv/bin/python compare_4way.py"
  echo " 用途：现场演示的兜底材料 —— 若现场代码跑不起来，打开本文档直接念结果"
  echo "================================================================"
  echo
  ~/shixun-venv/bin/python compare_4way.py 2>&1 | tr '\r' '\n' | grep -vE '^Loading weights'
  echo
  echo "================================================================"
  echo " 存档结束"
  echo "================================================================"
} | tee "$OUT"
