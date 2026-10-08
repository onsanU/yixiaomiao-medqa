# -*- coding: utf-8 -*-
"""
🎵 网易云音乐搜索代理（黑黑页面 AI 音乐推荐用）
纯 urllib 实现，零第三方依赖。
接口由 main.py 暴露：
  GET /music/search?kw=轻音乐&limit=6  → {"songs": [{id, name, artist, duration}]}
  GET /music/url?id=xxx                → {"url": "https://...mp3"}
"""
import json
import urllib.request
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://music.163.com",
    "Cookie": "appver=2.0.2",
}


def _get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def search_songs(kw, limit=6):
    """搜索歌曲 → [{id, name, artist, duration}]"""
    url = "https://music.163.com/api/search/get/web?" + urllib.parse.urlencode({
        "s": kw, "type": 1, "limit": limit, "offset": 0,
    })
    data = _get(url)
    songs = (data.get("result") or {}).get("songs") or []
    out = []
    for s in songs:
        artist = ", ".join(a.get("name", "") for a in (s.get("artists") or []))
        out.append({
            "id": s.get("id"),
            "name": s.get("name", ""),
            "artist": artist,
            "duration": s.get("duration", 0),
        })
    return out


def get_song_url(song_id):
    """取播放地址（有时效约20分钟，每次播放前现取）→ {url} 或 None（付费/失败）"""
    url = "https://music.163.com/api/song/enhance/player/url?" + urllib.parse.urlencode({
        "id": song_id, "ids": "[" + str(song_id) + "]", "br": 128000,
    })
    data = _get(url)
    items = data.get("data") or []
    if not items or not items[0].get("url"):
        return None
    u = items[0]["url"]
    # http → https：公网隧道(https)下防 mixed content 拦截
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    return {"url": u}
