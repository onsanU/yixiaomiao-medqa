# -*- coding: utf-8 -*-
"""
🐱 医疗问答交互版（试用模式）
用法：
  1. 先启动 Ollama（bash start_ollama.sh）
  2. 运行：python demo_chat.py
  3. 输入问题回车，直接问答；输入 exit 或 拜拜 退出
"""
import os, shutil
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"   # 跑腿小弟
LLM_MODEL = "qwen3.5:4b"               # 掌勺大厨
DB_DIR = "./chroma_demo_db"

# ── 药柜进货（demo用的8条医疗知识，正式项目会换真实资料）──
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

print("🐾 咪咪正在准备药柜和大厨，第一次启动会慢一点（要加载模型）...")
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=BASE)
llm = ChatOllama(model=LLM_MODEL, base_url=BASE, temperature=0.3)

splitter = RecursiveCharacterTextSplitter(chunk_size=80, chunk_overlap=20)
texts = splitter.split_text("\n".join(knowledge))
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
vectorstore = Chroma(embedding_function=embeddings, persist_directory=DB_DIR)
vectorstore.add_texts(texts)
print(f"🗄️ 药柜上架 {len(texts)} 块知识，大厨就位！")

def rag_answer(question: str):
    docs = vectorstore.similarity_search(question, k=2)
    context = "\n".join(d.page_content for d in docs)
    prompt = f"""你是一个专业的医疗健康问答助手。请只根据下面的参考资料回答用户问题。
如果资料里没有相关信息，请如实说明"资料库中暂无相关内容，建议咨询医生"。

【参考资料】
{context}

【用户问题】
{question}

请用中文简洁回答："""
    return llm.invoke(prompt).content

print("=" * 56)
print("🐱 咪咪版医疗问答助手 已开业！直接输入问题即可~")
print("💡 试试：感冒怎么办？血压高注意什么？失眠怎么改善？")
print("💡 输入 exit 或 拜拜 结束营业")
print("=" * 56)

while True:
    try:
        q = input("\n🧑 主人问：").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 收工啦，主人下次再来玩喵~")
        break
    if not q:
        continue
    if q.lower() in ("exit", "quit", "拜拜", "再见", "退出"):
        print("👋 收工啦，主人下次再来玩喵~")
        break
    try:
        print(f"🐱 Qwen答：{rag_answer(q)}")
    except Exception as e:
        print(f"⚠️ 出错了喵：{e}（检查一下 Ollama 启动了没？）")
