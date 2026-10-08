#!/usr/bin/env bash
# 演示存档结构验证：表头 / 3题 / 9结果块 / 结束标记 / 无 tqdm 脏数据
# 用法: bash verify_archive.sh
set -uo pipefail
cd "$(dirname "$0")"

F="$(dirname "$0")/../演示输出存档_compare4way.txt"
fail=0
chk() { [ "$2" = "$3" ] && echo "  ✅ $1: $2" || { echo "  ❌ $1: 期望 $3, 实际 $2"; fail=1; }; }

[ -s "$F" ] || { echo "❌ 存档文件不存在或为空: $F"; exit 1; }

chk "表头存在"   "$(grep -c '演示输出存档 · compare_4way.py' "$F")" 1
chk "题目数"     "$(grep -c '^问题[123]:' "$F")" 3
chk "结果块数"   "$(grep -cE '^【(原版|\+医疗LoRA)' "$F")" 9
chk "结束标记"   "$(grep -c '四版对比完成' "$F")" 1
chk "tqdm 残留"  "$(grep -c 'Loading weights' "$F")" 0
chk "回车符残留" "$(grep -c $'\r' "$F")" 0

[ "$fail" -eq 0 ] || { echo; echo "❌ 存档验证失败"; exit 1; }
echo
echo "🎉 存档验证 ALL PASS（表头/3题/9结果块/结束标记齐，无脏数据）"
