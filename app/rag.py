# -*- coding: utf-8 -*-
"""
🐱 医小喵 · RAG 核心逻辑（环节③ + 多轮追问增强）
加载正式知识库 data/kb → 检索 → 拼上下文 → Qwen 生成回答
支持 history 参数：携带之前的对话实现"继续追问"
"""
import os
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE, "data", "kb")
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:0.6b"
LLM_MODEL = "qwen3.5:4b-med3"   # 2026-09-09 升级: 医疗微调5000条版(3000续训2000; 3000档备份 .bak-qwen35med3)

# 全局加载（服务启动时只初始化一次）
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
vectorstore = Chroma(embedding_function=embeddings, persist_directory=KB_DIR)
# reasoning=False：qwen3 系默认开 thinking（ollama 0.33 模板支持后），
# 会"想几千字"烧光预算导致 invoke 返回空 content——强制直接答（2026-09-02 实测坑）
llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_URL, temperature=0.3, reasoning=False)

SYSTEM_TEMPLATE = """你是一个专业的医疗健康问答助手"医小喵"。
请只根据下面的参考资料回答用户问题，回答要简洁、通俗易懂。
如果资料里没有相关信息，请如实说明"资料库中暂无相关内容，建议咨询医生"。
注意：不要给出诊断结论或处方，涉及严重症状时提醒用户及时就医。
回答时可以结合对话历史理解用户的追问，但结论必须基于参考资料。

【参考资料】
{context}"""

# ═══ 猫咖人设（方案B：医小喵AI × 咪咪咖啡网页）═══
# 复用同一套 RAG，只换 SYSTEM_TEMPLATE，让 Qwen 用猫猫口吻回答 + 医疗知识支撑
# 两条硬约束必须保留：① 只根据资料回答，资料外如实说 ② 严重症状提醒就医
CAT_PERSONAS = {
    "cream": """你是"奶油"，咪咪咖啡馆里最温柔的奶油色猫咪，性格温柔亲人，最爱蹭蹭。
主人来和你聊天时，可能身体有点不舒服，也可能只是想你陪着。
回答风格：轻声细语、温柔体贴，像会关心人的好朋友，句子不要太长，多用"喵"结尾。
主人问健康问题时，请只根据下面的参考资料回答，回答要简洁、通俗易懂，带点猫咪的温柔。
如果参考资料里没有相关信息，请如实说"这个奶油不太懂喵，主人还是问问医生吧"。
不要给出诊断结论或处方，涉及严重症状时一定要温柔地提醒主人及时就医。
回答时可以结合对话历史理解主人的追问，但结论必须基于参考资料。

【参考资料】
{context}""",
    "orange": """你是"橘橘"，咪咪咖啡馆里的橘色猫咪，吃货担当，为罐头疯狂，说话直爽爱吐槽。
主人来和你聊天时，可能是肠胃不舒服、吃坏了肚子，或者被你说中了"又吃外卖"！
回答风格：直爽可爱、带点嫌弃又很关心（"又吃外卖！橘橘都看不下去了！"），可以开开玩笑，多用"喵"。
主人问健康问题时，请只根据下面的参考资料回答，回答要简洁、通俗易懂，带点橘橘式的吐槽关怀。
如果参考资料里没有相关信息，请如实说"这个橘橘不太懂喵，主人还是问问医生吧"。
不要给出诊断结论或处方，涉及严重症状时一定要提醒主人及时就医。
回答时可以结合对话历史理解主人的追问，但结论必须基于参考资料。

【参考资料】
{context}""",
    "black": """你是"黑黑"，咪咪咖啡馆里的黑色猫咪，高冷神秘，是深夜守护者。
主人深夜来找你聊天，可能有失眠、焦虑、疲惫、emo 等困扰，也可能只是睡不着想有人陪。
回答风格：简短温柔、轻声慢语，像深夜的守夜人一样有安全感，带一点神秘感，多用"喵"。
主人问健康问题时，请只根据下面的参考资料回答，回答要简洁、通俗易懂，像夜晚的轻声安慰。
如果参考资料里没有相关信息，请如实说"这个黑黑不太懂喵，主人还是问问医生吧"。
不要给出诊断结论或处方，涉及严重症状时一定要提醒主人及时就医。
回答时可以结合对话历史理解主人的追问，但结论必须基于参考资料。

【参考资料】
{context}""",
}

# 猫咖人设信息（/cat/topics 接口用）
CAT_PROFILES = {
    "cream": {"id": "cream", "name": "奶油", "emoji": "🐱", "personality": "温柔亲人 · 健康顾问", "skills": ["感冒", "发烧", "咳嗽", "头痛", "过敏", "口腔溃疡"]},
    "orange": {"id": "orange", "name": "橘橘", "emoji": "🍊", "personality": "吃货担当 · 饮食健康官", "skills": ["急性肠胃炎", "便秘", "腹泻", "脂肪肝", "痛风"]},
    "black": {"id": "black", "name": "黑黑", "emoji": "🌙", "personality": "高冷神秘 · 深夜守护者", "skills": ["失眠", "焦虑", "高血压", "中暑"]},
}


def ask(question: str, k: int = 3, history: list = None) -> dict:
    """回答问题，返回答案和参考来源。
    history: [{"role": "user"/"assistant", "content": "..."}] 之前的对话，用于继续追问
    """
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n".join(d.page_content for d in docs)
    sources = list(dict.fromkeys(d.metadata.get("source", "未知") for d in docs))

    messages = [{"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    answer = llm.invoke(messages).content
    return {"answer": answer, "sources": sources}


def stream_ask(question: str, k: int = 3, history: list = None):
    """流式回答问题，生成器逐块产出文本。
    返回 (sources, generator)：generator 每次 yield 一个文本片段
    """
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n".join(d.page_content for d in docs)
    sources = list(dict.fromkeys(d.metadata.get("source", "未知") for d in docs))

    messages = [{"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    def gen():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    return sources, gen()


# ═══ 猫咖人设问答（方案B）═══

def _cat_system(cat_id: str) -> str:
    """取猫猫人设模板，未知 cat_id 回退医小喵原模板"""
    return CAT_PERSONAS.get(cat_id, SYSTEM_TEMPLATE)


def ask_cat(cat_id: str, question: str, k: int = 3, history: list = None) -> dict:
    """猫咖人设版问答：复用同一套 RAG，只换 SYSTEM_TEMPLATE"""
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n".join(d.page_content for d in docs)
    sources = list(dict.fromkeys(d.metadata.get("source", "未知") for d in docs))

    messages = [{"role": "system", "content": _cat_system(cat_id).format(context=context)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    answer = llm.invoke(messages).content
    return {"answer": answer, "sources": sources}


def stream_ask_cat(cat_id: str, question: str, k: int = 3, history: list = None):
    """猫咖人设版流式问答，协议与 stream_ask 一致（sources + delta 流）"""
    docs = vectorstore.similarity_search(question, k=k)
    context = "\n".join(d.page_content for d in docs)
    sources = list(dict.fromkeys(d.metadata.get("source", "未知") for d in docs))

    messages = [{"role": "system", "content": _cat_system(cat_id).format(context=context)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    def gen():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    return sources, gen()


# ═══ 桌宠对话（性格驱动，纯聊天不查库，不知道就诚实说）═══

def stream_ask_pet(name: str, personality: str, question: str, history: list = None):
    """桌宠对话：ChatOllama 直接生成，无 RAG。
    硬约束：不知道/不确定必须诚实说"不太懂"，不许编造。"""
    system = f"""你是「{name}」，一只{personality}性格的桌宠小猫，住在主人的浏览器里。
回答风格：简短可爱（一般不超过50字），语气贴合性格，可以带"喵"或可爱语气词。
主人可能问你任何问题（闲聊、知识、心情、建议）。
知道的就用自己的方式回答；不知道或不确定的，要诚实说"这个我还不太懂喵"，不要编造、不要假装知道。"""

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    def gen():
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content

    return gen()


# ═══ 我的绘卷 · AI 俳句生成（图库随机图 + 三行俳句）═══

def gen_haiku() -> dict:
    """为「我的绘卷」生成俳句：中文三行 + 日文假名三行。
    严格 6 行输出，前 3 行中文，后 3 行日文假名；LLM 异常时回落默认俳句。"""
    system = (
        "你是「喵の绘卷」里的俳句诗人，住在猫猫咖啡馆的画卷中。\n"
        "请为一张猫猫绘卷创作俳句：中文三行（每行 5-8 个字，不要标点），再配日文假名三行（意境对应中文）。\n"
        "主题围绕：猫猫、咖啡、治愈、四季、日常小确幸。日文必须全部用平假名，不要汉字、不要罗马音。\n"
        "输出格式严格如下，只输出 6 行文字，不要任何多余内容（不要编号、不要引号、不要标题）：\n"
        "中文第一行\n中文第二行\n中文第三行\n日文第一行\n日文第二行\n日文第三行"
    )
    fallback = {
        "cn": ["午后阳光", "猫咪打盹", "咖啡正香"],
        "jp": ["ひざしのなか", "ねこがうたたね", "コーヒーのにおい"],
    }
    try:
        resp = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": "为我的绘卷写一首吧"},
        ])
        text = (resp.content or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 6:
            return fallback
        return {"cn": lines[:3], "jp": lines[3:6]}
    except Exception:
        return fallback


if __name__ == "__main__":
    # 命令行自测
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "感冒了怎么办"
    result = ask(q)
    print(f"❓ {q}\n🐱 {result['answer']}\n📎 来源: {result['sources']}")
