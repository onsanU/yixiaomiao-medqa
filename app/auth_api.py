# -*- coding: utf-8 -*-
"""
🐱 医小喵 · 认证 API（第6次迭代：账号密码登录，2026-09-07）
路由前缀 /auth（main.py 注册）；管理端点前缀 /admin/api（admin_api.py 引入）

接口：
  POST   /auth/register   {username, password}       注册（首个账号自动为 admin）
  POST   /auth/login      {username, password}       登录 → {token, username, role, expires_at}
  POST   /auth/logout     带 X-Auth-Token            登出（吊销会话）
  GET    /auth/me         带 X-Auth-Token            {username, role, created_at}
  POST   /auth/reset      {username, new_password}   [admin] 重置任意用户密码
  GET    /admin/api/users-accounts                    [admin] 注册账号列表（admin_api 提供）
"""
import re
import time

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel

from app import db
from app.auth import (hash_password, verify_password, new_token_pair,
                      token_expires_at, current_user, current_admin,
                      USERNAME_RE)

router = APIRouter()

# 登录/注册防爆破：ip -> [失败次数, 窗口起始时间]（5 次/分钟）
_fail = {}
_LIMIT = 5
_WINDOW = 60
# 恒时防枚举：用户不存在时也对这个假哈希做一次完整 PBKDF2 比较
_DUMMY_HASH = hash_password("dummy-timing-equalizer")


class CredReq(BaseModel):
    username: str
    password: str


class ResetReq(BaseModel):
    username: str
    new_password: str


class RoleReq(BaseModel):
    username: str
    role: str  # admin | user


def _client_ip(req: Request) -> str:
    # 公网反代后取 X-Forwarded-For（单层信任；frp/cloudflare 场景够用）
    fwd = req.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (req.client.host if req.client else "?")


def _allow(req: Request) -> bool:
    ip = _client_ip(req)
    now = time.time()
    rec = _fail.get(ip)
    if not rec or now - rec[1] > _WINDOW:
        _fail[ip] = [0, now]
        return True
    if rec[0] >= _LIMIT:
        return False
    return True


def _note_fail(req: Request) -> None:
    ip = _client_ip(req)
    now = time.time()
    rec = _fail.get(ip)
    if not rec or now - rec[1] > _WINDOW:
        _fail[ip] = [1, now]
    else:
        rec[0] += 1


def _valid_username(u: str) -> bool:
    return bool(re.fullmatch(USERNAME_RE, u))


def _issue_session(username: str) -> dict:
    """建会话 → {token, username, expires_at}（明文 token 只此一次）"""
    plain, token_hash = new_token_pair()
    expires = token_expires_at()
    if not db.create_session(token_hash, username, expires):
        raise HTTPException(status_code=500, detail="会话创建失败，请重试")
    return {"token": plain, "username": username, "expires_at": expires}


@router.post("/register")
def register(req: CredReq, http: Request):
    """注册（首个账号自动提升为 admin）。成功即自动登录返回 token"""
    if not _allow(http):
        raise HTTPException(status_code=429, detail="操作太频繁，请 1 分钟后再试")
    username = req.username.strip()
    password = req.password
    if not _valid_username(username):
        raise HTTPException(status_code=400, detail="用户名需 2-20 位中文/字母/数字/下划线")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if db.get_user(username):
        _note_fail(http)
        raise HTTPException(status_code=409, detail="用户名已存在")
    # 首个注册用户 = 管理员（第6次迭代设计）
    role = "admin" if db.count_users() == 0 else "user"
    if not db.create_user(username, hash_password(password), role):
        raise HTTPException(status_code=409, detail="用户名已存在")
    sess = _issue_session(username)
    return {"message": "注册成功", "role": role, **sess}


@router.post("/login")
def login(req: CredReq, http: Request):
    """登录：恒时比较防枚举 + 限流防爆破 → {token, username, role, expires_at}"""
    if not _allow(http):
        raise HTTPException(status_code=429, detail="尝试次数过多，请 1 分钟后再试")
    username = req.username.strip()
    user = db.get_user(username)
    # 恒时：无论账号是否存在都执行一次完整哈希比较（防用户名枚举）
    ok = verify_password(req.password, user["password_hash"] if user else _DUMMY_HASH)
    if not user or not ok:
        _note_fail(http)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    sess = _issue_session(username)
    return {"role": user["role"], **sess}


@router.post("/logout")
def logout(x_auth_token: str = Header(None)):
    if not x_auth_token:
        return {"ok": True}
    import hashlib
    db.delete_session(hashlib.sha256(x_auth_token.encode()).hexdigest())
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    """当前登录用户信息（前端启动时校验 token 有效性）"""
    return {"username": user["username"], "role": user["role"],
            "created_at": user.get("created_at")}


@router.post("/reset")
def reset_password_admin(req: ResetReq, admin: dict = Depends(current_admin)):
    """[管理后台] 重置任意用户密码（忘记密码的唯一途径——密码不可查看只能重置）"""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if not db.get_user(req.username.strip()):
        raise HTTPException(status_code=404, detail="用户不存在")
    db.update_user(req.username.strip(), password_hash=hash_password(req.new_password))
    db.delete_user_sessions(req.username.strip())  # 吊销该用户全部会话，强制重新登录
    return {"message": f"已重置 {req.username.strip()} 的密码并使其重新登录"}


@router.post("/role")
def change_role(req: RoleReq, admin: dict = Depends(current_admin)):
    """[管理后台] 切换用户角色（admin/user）；防自降级"""
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="角色只能是 admin 或 user")
    if not db.get_user(req.username.strip()):
        raise HTTPException(status_code=404, detail="用户不存在")
    if req.username.strip() == admin["username"] and req.role != "admin":
        raise HTTPException(status_code=400, detail="不能取消自己的管理员角色")
    db.update_user(req.username.strip(), role=req.role)
    if req.role == "user":
        db.delete_user_sessions(req.username.strip())  # 降级立即失效其会话
    return {"message": f"{req.username.strip()} 的角色已设为 {req.role}"}
