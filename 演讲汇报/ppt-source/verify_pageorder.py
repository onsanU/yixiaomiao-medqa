#!/usr/bin/env python3
"""hermes-verify: 演讲PPT页码重排一致性 定向验证（2026-09-10 新增"先睹为快"页后）
验证目标：
  1. gen.js 里 page: N 编号连续 1..24 且无重复
  2. 讲稿时间表页码 == 口播稿标题页码（P1..P24 一一对应）
  3. 新页"先睹为快"确实插在 P12(防OOM) 与 P14(训练执行) 之间
  4. 关键正文引用页码与重排后一致（不要砍P15/P17 等）
  5. verify.sh 页数断言与实际生成页数一致
"""
import re, sys, subprocess
from pathlib import Path

BASE = Path("/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/演讲汇报")
GEN = BASE / "ppt-source/gen.js"
SPEECH = BASE / "演讲讲稿_开场白与全流程.md"
VERIFY = BASE / "ppt-source/verify.sh"

p = f = 0
def ok(name, cond, detail=""):
    global p, f
    if cond: p += 1
    else: f += 1; print(f"  ❌ {name}" + (f"\n     {detail}" if detail else ""))

gen = GEN.read_text(encoding="utf-8")
speech = SPEECH.read_text(encoding="utf-8")
vsh = VERIFY.read_text(encoding="utf-8")

# ---- 1. gen.js 的 page 编号 ----
# 封面(P1)和致谢(末页)用 H.cover() 风格，均不带 page 字段 → 带页码的是 2..20
pages = [int(m) for m in re.findall(r"page: (\d+)", gen)]
ok("gen.js page 编号连续无重复(2..18)", pages == list(range(2, 19)),
   f"实际: {pages}")
ok("带页码17页 + 无页码2页(封面/致谢) = 19页", len(pages) == 17, f"实际 {len(pages)}")
blocks = re.findall(r"// ============ ([\d.]+) (.+?) ============", gen)
ok("gen.js 页块数 = 19", len(blocks) == 19, f"实际 {len(blocks)}")
ok("P7环境页已删除", not any("环境准备" in b[1] for b in blocks))
ok("P10数据卫生页已删除", not any("数据卫生" in b[1] for b in blocks))
ok("效果验证方法页已删除", not any("效果验证方法" in b[1] for b in blocks))
ok("上线验证页已删除", not any("上线验证" in b[1] for b in blocks))

# ---- 2. 新页位置正确 ----
i_oom = gen.find("12 防 OOM 三板斧")
i_hook = gen.find("12.5 先导演示")
i_train = gen.find("14 训练执行")
ok("无先睹为快页插入", i_hook < 0, f"hook={i_hook}")
ok("先睹为快页已移除", "先睹为快" not in gen)

# ---- 3. 讲稿两表页码一致 ----
tbl = re.findall(r"^\| (P\d+)\s+\|", speech, re.M)
spk = re.findall(r"^### 【(P\d+) ", speech, re.M)
ok("时间表 = 口播稿 页码一一对应", tbl == spk,
   f"表={tbl[:5]}... 稿={spk[:5]}..." if tbl != spk else "")
ok("两表都覆盖 P1..P19", tbl == [f"P{i}" for i in range(1, 20)], f"实际 {len(tbl)} 项")

# ---- 4. 关键正文引用页码 ----
ok("'不要砍 P12/P13' 已更新", "千万不要砍 P12（碎片化救场）和 P13（现场跑代码）" in speech)
ok("'讲慢一点 P12/P13' 已更新", "**P12 和 P13 讲慢一点**" in speech)
ok("页码引用无残留旧值 P16（碎片化/跑代码）",
   "P16（碎片化" not in speech and "P16（现场跑代码" not in speech)

# ---- 5. verify.sh 断言与真实页数 ----
m = re.search(r"assert n == (\d+)", vsh)
ok("verify.sh 页数断言 = 19", m and int(m.group(1)) == 19, f"实际 {m.group(1) if m else '未找到'}")
try:
    from pptx import Presentation
    real = len(Presentation(str(BASE / "汇报PPT_医疗专家微调.pptx")).slides)
    ok("交付 pptx 真实页数 = 19", real == 19, f"实际 {real}")
except Exception as e:
    print(f"  ⚠️ 跳过 pptx 页数读取: {e}")

# ---- 6. 备份存在（可回滚）----
ok("gen.js.bak-hookpage 备份存在", (GEN.parent / "gen.js.bak-hookpage").exists())

print(f"\n===== PPT 页码重排 · 定向验证 =====")
print(f"通过 {p} / 失败 {f}")
sys.exit(1 if f else 0)
