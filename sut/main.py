"""被测服务（SUT）：若依后台的接口契约模拟器。

它的定位不是"假数据"，而是「被测服务的接口契约」：
  - 行为与真实若依保持一致（业务失败返回 HTTP 200 + code 500）
  - 让 CI 能秒级起环境，保证流水线红灯一定是代码问题，不是环境问题
  - 让框架可以被独立验证

启动：uvicorn sut.main:app --port 8000
文档：http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="SUT-Mock · 若依接口契约模拟器", version="1.0.0")

VALID_TOKEN = "mock-token-for-automation"
ADMIN_PASSWORD = "admin123"
ADMIN_USER_ID = 1
MAX_USERNAME_LEN = 30

_lock = threading.Lock()

_users: dict[int, dict[str, Any]] = {
    1: {
        "userId": 1, "userName": "admin", "nickName": "超级管理员",
        "email": "admin@demo.com", "status": "0", "createTime": "2026-11-01 10:00:00",
    },
    2: {
        "userId": 2, "userName": "test01", "nickName": "测试用户01",
        "email": "test01@demo.com", "status": "0", "createTime": "2026-11-02 09:30:00",
    },
}
_next_id = 3


def _ok(data: Any = None, **extra) -> dict:
    body = {"code": 200, "msg": "操作成功"}
    if data is not None:
        body["data"] = data
    body.update(extra)
    return body


def _fail(msg: str) -> dict:
    return {"code": 500, "msg": msg}


def _unauthorized() -> JSONResponse:
    return JSONResponse(status_code=401, content={"code": 401, "msg": "认证失败，无法访问系统资源"})


def _check_auth(request: Request) -> bool:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False
    return header.split(" ", 1)[1].strip() == VALID_TOKEN


# ---------------------------------------------------------------- 登录


@app.post("/login")
async def login(payload: dict) -> Any:
    username = payload.get("username", "")
    password = payload.get("password", "")
    # 与真实若依一致：账号不存在与密码错误返回同一提示，避免账号枚举
    if username != "admin" or password != ADMIN_PASSWORD:
        return _fail("用户不存在/密码错误")
    return {"code": 200, "msg": "操作成功", "token": VALID_TOKEN}


@app.get("/captchaImage")
async def captcha_image() -> dict:
    return {"code": 200, "msg": "操作成功", "captchaEnabled": False, "uuid": ""}


# ---------------------------------------------------------------- 用户管理


@app.get("/system/user/list")
async def list_users(
    request: Request,
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    userName: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    with _lock:
        items = list(_users.values())

    if userName:
        items = [u for u in items if userName in u["userName"]]
    if status:
        items = [u for u in items if u["status"] == status]

    items.sort(key=lambda u: u["userId"])
    total = len(items)
    start = max(0, (pageNum - 1) * pageSize)
    rows = items[start:start + pageSize] if pageSize > 0 else []

    return {"code": 200, "msg": "查询成功", "total": total, "rows": rows}


@app.post("/system/user")
async def add_user(request: Request, payload: dict) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    global _next_id
    username = (payload.get("userName") or "").strip()
    if not username:
        return _fail("用户账号不能为空")
    if len(username) > MAX_USERNAME_LEN:
        return _fail(f"用户账号长度不能超过{MAX_USERNAME_LEN}个字符")

    with _lock:
        if any(u["userName"] == username for u in _users.values()):
            return _fail(f"新增用户'{username}'失败，用户账号已存在")
        user_id = _next_id
        _next_id += 1
        _users[user_id] = {
            "userId": user_id,
            "userName": username,
            "nickName": payload.get("nickName", username),
            "email": payload.get("email", ""),
            "status": payload.get("status", "0"),
            "remark": payload.get("remark", ""),
            "createTime": "2026-11-18 20:00:00",
        }
    return _ok()


@app.get("/system/user/{user_id}")
async def get_user(request: Request, user_id: int) -> Any:
    if not _check_auth(request):
        return _unauthorized()
    with _lock:
        user = _users.get(user_id)
    if not user:
        return _fail("用户不存在")
    return _ok(dict(user))


@app.put("/system/user")
async def update_user(request: Request, payload: dict) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    user_id = payload.get("userId")
    if not user_id:
        return _fail("用户ID不能为空")

    with _lock:
        user = _users.get(user_id)
        if not user:
            return _fail("用户不存在")

        new_name = payload.get("userName")
        if new_name and new_name != user["userName"]:
            if any(u["userName"] == new_name and u["userId"] != user_id for u in _users.values()):
                return _fail(f"修改用户'{new_name}'失败，用户账号已存在")
            user["userName"] = new_name

        for field in ("nickName", "email", "status", "remark"):
            if field in payload:
                user[field] = payload[field]

    return _ok()


@app.delete("/system/user/{user_ids}")
async def delete_user(request: Request, user_ids: str) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    ids = [int(i) for i in user_ids.split(",") if i.strip().isdigit()]
    if ADMIN_USER_ID in ids:
        return _fail("不允许操作超级管理员用户")

    with _lock:
        for user_id in ids:
            _users.pop(user_id, None)
    return _ok()


@app.get("/")
async def index() -> dict:
    return {"service": "SUT-Mock", "docs": "/docs", "users": 2}






# ---------------------------------------------------------------- 角色管理
# 1. 先定义角色的 Mock 数据结构
_roles: dict[int, dict[str, Any]] = {
    1: {
        "roleId": 1, "roleName": "超级管理员", "roleKey": "admin",
        "roleSort": 1, "status": "0", "createTime": "2026-11-01 10:00:00",
    },
    2: {
        "roleId": 2, "roleName": "普通角色", "roleKey": "common",
        "roleSort": 2, "status": "0", "createTime": "2026-11-02 09:30:00",
    },
}
_next_role_id = 3

# 2. 实现 4 个 Role 接口
@app.get("/system/role/list")
async def list_roles(
    request: Request,
    pageNum: int = Query(1),
    pageSize: int = Query(10),
    roleName: Optional[str] = Query(None),
) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    with _lock:
        items = list(_roles.values())

    # 支持 roleName 过滤
    if roleName:
        items = [r for r in items if roleName in r["roleName"]]

    items.sort(key=lambda r: r["roleId"])
    total = len(items)
    start = max(0, (pageNum - 1) * pageSize)
    rows = items[start:start + pageSize] if pageSize > 0 else []

    return {"code": 200, "msg": "查询成功", "total": total, "rows": rows}


@app.post("/system/role")
async def add_role(request: Request, payload: dict) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    global _next_role_id
    role_name = (payload.get("roleName") or "").strip()
    role_key = (payload.get("roleKey") or "").strip()

    if not role_name or not role_key:
        return _fail("角色名称和权限字符不能为空")

    with _lock:
        # roleKey 重复返回 code 500
        if any(r["roleKey"] == role_key for r in _roles.values()):
            return _fail("角色权限字符已存在")
        
        role_id = _next_role_id
        _next_role_id += 1
        _roles[role_id] = {
            "roleId": role_id,
            "roleName": role_name,
            "roleKey": role_key,
            "roleSort": payload.get("roleSort", 0),
            "status": payload.get("status", "0"),
            "createTime": "2026-11-22 12:00:00",
        }
    return _ok()


@app.put("/system/role")
async def update_role(request: Request, payload: dict) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    role_id = payload.get("roleId")
    if not role_id:
        return _fail("角色ID不能为空")

    with _lock:
        role = _roles.get(role_id)
        if not role:
            return _fail("角色不存在")

        # 修改 roleName
        new_name = payload.get("roleName")
        if new_name:
            role["roleName"] = new_name
            
        # 如果想改 roleKey，也得校验重复
        new_key = payload.get("roleKey")
        if new_key and new_key != role["roleKey"]:
            if any(r["roleKey"] == new_key and r["roleId"] != role_id for r in _roles.values()):
                return _fail("角色权限字符已存在")
            role["roleKey"] = new_key

    return _ok()


@app.delete("/system/role/{role_ids}")
async def delete_role(request: Request, role_ids: str) -> Any:
    if not _check_auth(request):
        return _unauthorized()

    ids = [int(i) for i in role_ids.split(",") if i.strip().isdigit()]
    
    # roleId=1（超管）返回 500
    if 1 in ids:
        return _fail("不允许操作超级管理员")

    with _lock:
        for role_id in ids:
            _roles.pop(role_id, None)
    return _ok()