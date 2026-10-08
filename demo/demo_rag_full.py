# -*- coding: utf-8 -*-
"""
🐱 迷你版 RAG 心脏合体（第0步 · 第三步）
完整流程：提问 → 跑腿小弟(embedding)检索药柜(ChromaDB) → 拼上下文 → Qwen大厨照着知识炒菜
这就是整个医疗问答项目的核心骨架喵！
"""
import os, shutil
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"   # 跑腿小弟
LLM_MODEL = "qwen3.5:4b"               # 掌勺大厨
DB_DIR = "./chroma_demo_db"

# ── 1. 请出跑腿小弟 + 大厨 ──
print("🐾 请出跑腿小弟和掌勺大厨 ...")
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=BASE)
llm = ChatOllama(model=LLM_MODEL, base_url=BASE, temperature=0.3)

# ── 2. 药柜进货（和第二步同一批医疗知识）──
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

# ── 3. 切块 + 上架 ──
splitter = RecursiveCharacterTextSplitter(chunk_size=80, chunk_overlap=20)
texts = splitter.split_text("\n".join(knowledge))
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
vectorstore = Chroma(embedding_function=embeddings, persist_directory=DB_DIR)
vectorstore.add_texts(texts)
print(f"🗄️ 药柜上架 {len(texts)} 块知识")

# ── 4. 完整问答函数（RAG心脏！）──
def rag_answer(question: str):
    # ① 跑腿小弟检索：从药柜翻出最相关的知识
    docs = vectorstore.similarity_search(question, k=2)
    context = "\n".join(d.page_content for d in docs)
    # ② 拼"菜谱"：把知识喂给大厨当参考资料
    prompt = f"""你是一个专业的医疗健康问答助手。请只根据下面的参考资料回答用户问题。
如果资料里没有相关信息，请如实说明"资料库中暂无相关内容，建议咨询医生"。

【参考资料】
{context}

【用户问题】
{question}

请用中文简洁回答："""
    # ③ 大厨炒菜
    answer = llm.invoke(prompt).content
    return answer, docs

# ── 5. 现场演示 ──
questions = [
    "我感冒了，嗓子疼还发烧，应该怎么办？",
    "我妈妈血压有点高，平时要注意什么？",
    "最近总是失眠睡不着，有什么建议吗？",
    "火星上能种土豆吗？",  # 故意刁难：知识库没有的内容
]
for q in questions:
    print("\n" + "=" * 56)
    print(f"❓ 主人问：{q}")
    answer, docs = rag_answer(q)
    print(f"🐱 Qwen答：{answer}")
    print(f"   📎 参考了药柜：{len(docs)} 块")

print("\n🎉 迷你RAG心脏合体成功！这就是项目核心的完整骨架喵~")
