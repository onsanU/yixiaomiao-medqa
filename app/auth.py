# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 认证核心（第6次迭代：账号密码登录，2026-09-07）
- 密码哈希：PBKDF2-HMAC-SHA256（标准库实现，60万次迭代，每用户随机盐）——绝不存明文
- 登录令牌：secrets.token_urlsafe(32) 明文发前端，库中只存 sha256 哈希（库泄露不可直接用）
- 会话：7 天有效期，服务端可吊销（登出/管理端踢人）
- 防爆破：登录/注册失败 5 次/分钟/IP（内存计数，够单机公网演示用）
- 防枚举：用户不存在也执行一次哈希比较（恒时响应）
"""
import hashlib
import hmac
import secrets
import datetime

from fastapi import Header, HTTPException, Depends

from app import db

TOKEN_TTL_DAYS = 7
PBKDF2_ITERATIONS = 600_000
USERNAME_RE = "^[\\u4e00-\\u9fa5A-Za-z0-9_]{2,20}$"  # 中文/字母/数字/下划线，2-20 位


# ── 密码哈希 ─────────────────────────────────────────
def hash_password(password: str) -> str:
    """返回 'pbkdf2_sha256$600000$<salt_hex>$<hash_hex>'"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """恒时比较（hmac.compare_digest），stored 格式异常返回 False"""
    try:
        algo, iters, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(dk.hex(), expected)
    except Exception:
        return False


# ── 登录令牌 ─────────────────────────────────────────
def new_token_pair() -> tuple:
    """返回 (明文token, sha256哈希)——明文只发前端一次，库中只存哈希"""
    plain = secrets.token_urlsafe(32)
    return plain, hashlib.sha256(plain.encode()).hexdigest()


def token_expires_at() -> str:
    return (datetime.datetime.now() + datetime.timedelta(days=TOKEN_TTL_DAYS)) \
        .strftime("%Y-%m-%d %H:%M:%S")


# ── FastAPI 鉴权依赖 ────────────────────────────────
def current_user(x_auth_token: str = Header(None)):
    """聊天接口依赖：校验 X-Auth-Token → 返回用户 dict（username/role）"""
    if not x_auth_token:
        raise HTTPException(status_code=401, detail="请先登录")
    token_hash = hashlib.sha256(x_auth_token.encode()).hexdigest()
    username = db.get_session_user(token_hash)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="账号不存在")
    return user


def current_admin(user: dict = Depends(current_user)):
    """管理 API 依赖：必须是 admin 角色（自动先过 current_user 鉴权）"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
