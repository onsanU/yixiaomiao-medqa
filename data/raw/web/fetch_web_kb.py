# -*- coding: utf-8 -*-
"""
🐱 知识库抓取工具：从 A+医学百科（a-hospital.com）批量抓取疾病条目
用法：python fetch_web_kb.py
产物：data/raw/web/<疾病名>.md（正文纯文本，含章节标题）
说明：curl 负责下载（稳），正则负责提取，不依赖第三方库
"""
import subprocess, urllib.parse, re, html as htmlmod, os

BASE_URL = "http://www.a-hospital.com/w/"
HERE = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(HERE, "html")
os.makedirs(HTML_DIR, exist_ok=True)

# 条目名 → 备用名（主条目抓不到时依次尝试）
DISEASES = {
    "感冒": [],
    "流行性感冒": [],
    "发烧": ["发热"],
    "咳嗽": [],
    "头痛": [],
    "失眠": [],
    "高血压": [],
    "糖尿病": [],
    "急性肠胃炎": ["肠胃炎"],
    "过敏": [],
    "口腔溃疡": [],
    "中暑": [],
    "扭伤": [],
    "近视": [],
    "颈椎病": [],
    "鼻炎": [],
    "支气管炎": [],
    "哮喘": [],
    "便秘": [],
    "腹泻": [],
    "咽喉炎": [],
    "湿疹": [],
    "荨麻疹": [],
    "贫血": [],
    "痛风": [],
    "关节炎": [],
    "脂肪肝": [],
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_html(name):
    """抓 HTML，返回 (html文本, 实际条目名) 或 (None, None)"""
    for cand in [name] + DISEASES[name]:
        enc = urllib.parse.quote(cand)
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "25", "-A", UA, f"{BASE_URL}{enc}"],
            capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 30000:
            return r.stdout, cand
    return None, None


def extract_content(html_text):
    """从 id=content 区域提取标题+段落+列表"""
    m = re.search(r'<div id="content">(.*?)<div id="footer"', html_text, re.S)
    body = m.group(1) if m else html_text
    body = re.sub(r'<table.*?</table>', '', body, flags=re.S)
    body = re.sub(r'<script.*?</script>|<style.*?</style>', '', body, flags=re.S)
    parts = re.findall(
        r'<h([23])[^>]*>(.*?)</h\1>|<p>(.*?)</p>|<li>(.*?)</li>', body, re.S)
    out = []
    for hlevel, h, p, li in parts:
        t = htmlmod.unescape(re.sub(r'<[^>]+>', '', (h or p or li))).strip()
        t = re.sub(r'\s+', ' ', t)
        if t:
            out.append(("#" * (int(hlevel) + 1) + " " + t) if h else t)
    return "\n".join(out)


ok, fail = [], []
for name in DISEASES:
    html_text, real_name = fetch_html(name)
    if not html_text:
        fail.append(name)
        print(f"❌ {name}: 抓取失败")
        continue
    text = extract_content(html_text)
    seen, lines = set(), []
    for ln in text.split("\n"):
        if ln not in seen:
            seen.add(ln)
            lines.append(ln)
    md = f"# {name}\n\n> 来源：A+医学百科（a-hospital.com）\n\n" + "\n".join(lines)
    with open(os.path.join(HERE, f"{name}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    ok.append(name)
    print(f"✅ {name}（实际条目:{real_name}）→ {len(md)} 字符")

print(f"\n完成：成功 {len(ok)} 条，失败 {len(fail)} 条")
if fail:
    print("失败条目：", "、".join(fail))
