#!/usr/bin/env bash
# 一键复验：生成 → 几何 → 内容 → (可选)视觉
# 用法: npm test            —— 快速三项
#       RUN_VISUAL=1 npm test —— 追加 Windows PowerPoint 渲染 + OCR 抽查
set -euo pipefail
cd "$(dirname "$0")"

QA_GEOM="$HOME/.hermes/skills/productivity/pptx-deck-generation/scripts/qa_geom.py"
OUT_DIR=/tmp/meow-ppt/verify_out
OUT_FILE="$OUT_DIR/verify_deck.pptx"
mkdir -p "$OUT_DIR"

echo "== 1/4 生成 pptx（输出到临时路径，不碰交付件）=="
OUT_FILE="$OUT_FILE" node gen.js

echo "== 2/4 几何越界检查（16:9 画布 10 x 5.625）=="
python3 "$QA_GEOM" "$OUT_FILE" > /tmp/meow-ppt/.qa_geom.log 2>&1
grep -q "无越界问题" /tmp/meow-ppt/.qa_geom.log || { grep -A8 "越界问题汇总" /tmp/meow-ppt/.qa_geom.log; exit 1; }
echo "✅ 无越界问题"

echo "== 3/4 内容检查（占位符 / 对象泄漏 / 页数）=="
python3 -m markitdown "$OUT_FILE" > /tmp/meow-ppt/.qa_text.log 2>&1
if grep -qE "object Object|TODO|占位|lorem|undefined|NaN" /tmp/meow-ppt/.qa_text.log; then
  echo "❌ 发现占位符或对象泄漏"; grep -nE "object Object|TODO|占位|undefined" /tmp/meow-ppt/.qa_text.log | head; exit 1
fi
python3 - <<'PY'
from pptx import Presentation
p = Presentation('/tmp/meow-ppt/verify_out/verify_deck.pptx')
n = len(p.slides)
assert n == 19, f'页数应为 19，实际 {n}'
assert abs(p.slide_width/914400 - 10) < 0.01, '画布宽度不是 10in'
print(f'✅ 内容干净，页数 {n}，画布 16:9')
PY

if [ "${RUN_VISUAL:-0}" = "1" ]; then
  echo "== 4/4 视觉层（Windows PowerPoint 渲染 + OCR 抽查）=="
  cp /tmp/meow-ppt/export_utf16.ps1 /mnt/d/tmp/meow-ppt/
  /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File 'D:\tmp\meow-ppt\export_utf16.ps1' | tail -2
  PYTHONPATH="$HOME/.local/lib/python3.12/site-packages" python3 ocr_check.py
else
  echo "== 4/4 视觉层 已跳过（RUN_VISUAL=1 npm test 可开启）=="
fi

echo
echo "🎉 ALL PASS —— 生成 + 几何 + 内容$([ "${RUN_VISUAL:-0}" = "1" ] && echo ' + 视觉') 全通过"
