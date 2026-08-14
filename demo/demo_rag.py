# -*- coding: utf-8 -*-
"""
🐱 迷你版 RAG 检索演示（第0步 · 第二步）
把医疗知识存进 ChromaDB 药柜，提问时用 bge-m3 跑腿小弟秒翻出来
"""
import os, shutil
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE = "http://localhost:11434"
DB_DIR = "./chroma_demo_db"

# ── 1. 请出跑腿小弟（embedding 模型：把文字变成"向量标签"）──
print("🐾 请出跑腿小弟 qwen3-embedding:0.6b ...")
embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b", base_url=BASE)

# ── 2. 药柜进货：几条医疗知识 ──
knowledge = [
    "感冒通常由病毒引起，症状包括流鼻涕、咳嗽、喉咙痛和发烧。多喝水、多休息，一般7-10天可自愈。如果发烧超过38.5度可服用退烧药。",
    "流行性感冒（流感）比普通感冒症状更重，常伴随高烧、全身酸痛和乏力。高危人群建议每年接种流感疫苗。",
    "失眠的改善方法：保持规律作息、睡前避免使用电子产品、减少咖啡因摄入、睡前可进行冥想或深呼吸放松。若持续失眠建议就医。",
    "高血压患者应低盐饮食（每日食盐不超过5克）、规律运动、控制体重、戒烟限酒，并遵医嘱规律服药，定期监测血压。",
    "糖尿病管理核心：控制饮食（少糖少油）、适度运动、监测血糖、按时用药。出现低血糖症状（心慌、出汗、手抖）应立即进食含糖食物。",
    "口腔溃疡多为自限性疾病，一般1-2周自愈。可补充维生素B族和维生素C，避免辛辣刺激食物，保持口腔清洁。反复发作或长期不愈应就医。",
    "急性肠胃炎常因不洁饮食引起，症状为腹痛、腹泻、恶心呕吐。应补充水分和电解质（口服补液盐），清淡饮食，严重脱水需就医输液。",
    "春季过敏常见症状为打喷嚏、流清涕、眼痒。可提前服用抗过敏药物，外出佩戴口罩，回家后清洗面部和鼻腔。",
]

# ── 3. 切块（大块知识切成小块，检索更精准）──
splitter = RecursiveCharacterTextSplitter(chunk_size=80, chunk_overlap=20)
texts = splitter.split_text("\n".join(knowledge))
print(f"📦 知识切块完成：{len(texts)} 块")

# ── 4. 入库 ChromaDB（药柜上架）──
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
vectorstore = Chroma(embedding_function=embeddings, persist_directory=DB_DIR)
vectorstore.add_texts(texts)
print(f"🗄️ 药柜入库完成：{len(texts)} 块知识已上架 → {DB_DIR}")

# ── 5. 检索测试（跑腿小弟找药）──
queries = ["我感冒了，嗓子疼还发烧，怎么办？", "晚上总是睡不着觉有什么办法？"]
for q in queries:
    print("\n" + "=" * 56)
    print(f"❓ 提问：{q}")
    results = vectorstore.similarity_search_with_score(q, k=2)
    for i, (doc, score) in enumerate(results, 1):
        print(f"  📄 第{i}相关 (距离{score:.3f})：{doc.page_content[:62]}...")

print("\n🎉 药柜+跑腿小弟验证完成！下一步就可以让 Qwen 大厨照着这些资料炒菜了喵~")
