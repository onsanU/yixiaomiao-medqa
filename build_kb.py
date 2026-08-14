# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 知识库构建脚本（环节④）
读取 data/raw/ 下所有 markdown 医疗资料 → 切块 → 向量化 → 存入 ChromaDB

用法：
    source ~/medqa-venv/bin/activate
    python build_kb.py

产物：data/kb/（ChromaDB 向量库，可反复重建）
"""
import os, glob, re
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_DIRS = [os.path.join(BASE, "data/raw/web"), os.path.join(BASE, "data/raw/manual")]
KB_DIR = os.path.join(BASE, "data/kb")
EMBED_MODEL = "qwen3-embedding:0.6b"
CHUNK_SIZE = 400   # 每块字符数
CHUNK_OVERLAP = 60 # 块间重叠

print("🐾 开始构建医小喵知识库 ...")

# ── 1. 读取所有资料 ──
docs = []  # (文本, 来源)
for d in RAW_DIRS:
    for md_path in sorted(glob.glob(os.path.join(d, "*.md"))):
        name = os.path.splitext(os.path.basename(md_path))[0]
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        # 去掉来源行和一级标题（保留章节内容）
        lines = [ln for ln in content.split("\n")
                 if not ln.startswith("> 来源") and not ln.startswith("# ")]
        text = "\n".join(lines).strip()
        if text:
            docs.append((text, name))

print(f"📄 读取资料：{len(docs)} 个主题")

# ── 2. 切块 ──
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
chunks, metas = [], []
for text, name in docs:
    parts = splitter.split_text(text)
    for p in parts:
        if len(p.strip()) >= 10:  # 过滤过短碎片
            chunks.append(p)
            metas.append({"source": name})
print(f"✂️  切块完成：{len(chunks)} 块")

# ── 3. 向量化入库 ──
print("🐾 请出跑腿小弟 qwen3-embedding:0.6b ...")
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url="http://localhost:11434")
if os.path.exists(KB_DIR):
    import shutil
    shutil.rmtree(KB_DIR)  # 重建药柜
vectorstore = Chroma(embedding_function=embeddings, persist_directory=KB_DIR)
vectorstore.add_texts(chunks, metadatas=metas)
print(f"🗄️  知识库构建完成！{len(chunks)} 块 → {KB_DIR}")

# ── 4. 抽样验证 ──
print("\n🧪 抽样验证检索效果：")
for q in ["感冒了怎么办", "血压高要注意什么", "崴了脚怎么处理"]:
    results = vectorstore.similarity_search_with_score(q, k=1)
    if results:
        doc, score = results[0]
        print(f"  ❓ {q} → [{doc.metadata.get('source')}] (距离{score:.3f}) {doc.page_content[:30]}...")
print("\n🎉 知识库构建完成！可以进入环节③正式版问答服务了喵~")
