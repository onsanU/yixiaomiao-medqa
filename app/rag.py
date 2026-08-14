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
LLM_MODEL = "qwen2.5:7b"

# 全局加载（服务启动时只初始化一次）
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
vectorstore = Chroma(embedding_function=embeddings, persist_directory=KB_DIR)
llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_URL, temperature=0.3)

SYSTEM_TEMPLATE = """你是一个专业的医疗健康问答助手"医小喵"。
请只根据下面的参考资料回答用户问题，回答要简洁、通俗易懂。
如果资料里没有相关信息，请如实说明"资料库中暂无相关内容，建议咨询医生"。
注意：不要给出诊断结论或处方，涉及严重症状时提醒用户及时就医。
回答时可以结合对话历史理解用户的追问，但结论必须基于参考资料。

【参考资料】
{context}"""


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


if __name__ == "__main__":
    # 命令行自测
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "感冒了怎么办"
    result = ask(q)
    print(f"❓ {q}\n🐱 {result['answer']}\n📎 来源: {result['sources']}")
