# -*- coding: utf-8 -*-
"""
🐱 第12步：SenseVoice ASR 服务（FastAPI 部署）
- 独立微服务：~/sensevoice-venv/bin/uvicorn asr_server:app --host 127.0.0.1 --port 8002
- 模型常驻内存，首次加载约 8s，之后秒回
- 接口：POST /asr  上传音频文件(file) → {"text": "识别文字"}
- 中文识别 + 标点 + 情感标记（SenseVoiceSmall 特色）
"""
import tempfile
import time
import os

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

MODEL_DIR = r"/mnt/d/Project/JXprojiect/Hermes-project/project/yixiaomiao-medqa/models/SenseVoiceSmall"
MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20MB 上限

app = FastAPI(title="医小喵 SenseVoice ASR 服务", version="1.0")

# 跨域放行（第14步界面化测试用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 懒加载单例：首次请求才加载模型（不拖慢服务启动）──
_model = None


def _get_model():
    global _model
    if _model is None:
        print("🎧 首次加载 SenseVoiceSmall ...", flush=True)
        t0 = time.time()
        _model = AutoModel(
            model=MODEL_DIR,
            device="cpu",
            disable_update=True,
            disable_pbar=True,
        )
        print(f"✅ 模型加载完成 {time.time()-t0:.1f}s", flush=True)
    return _model


@app.get("/health")
def health():
    return {"status": "ok", "service": "sensevoice-asr", "model_loaded": _model is not None}


@app.post("/asr")
async def asr(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_AUDIO_BYTES:
        return {"error": "音频太大，请控制在 20MB 内"}
    if len(data) < 100:
        return {"error": "音频文件为空或损坏"}

    # 存临时音频文件（浏览器录音是 webm/opus，必须转码）
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()
    wav16k = tmp.name.rsplit(".", 1)[0] + "_16k.wav"

    try:
        # ffmpeg 统一转 16kHz 单声道 wav（SenseVoice 最优输入格式）
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name,
             "-ar", "16000", "-ac", "1", wav16k],
            capture_output=True, timeout=180,  # 2026-09-08: 60→180，长音频文件转码留足余量
        )
        if r.returncode != 0:
            return {"error": "音频解码失败，请上传 wav/mp3/webm/m4a 格式"}

        model = _get_model()
        t0 = time.time()
        res = model.generate(
            input=wav16k,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60,
        )
        cost = time.time() - t0
        if res and "text" in res[0]:
            text = rich_transcription_postprocess(res[0]["text"])
            return {"text": text, "cost_s": round(cost, 2), "filename": file.filename}
        return {"error": "未识别到内容", "cost_s": round(cost, 2)}
    finally:
        os.unlink(tmp.name)
        if os.path.exists(wav16k):
            os.unlink(wav16k)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
