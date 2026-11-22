"""用例级 fixture：造数 / 清数。

核心原则：每条用例自己准备数据、自己收拾干净。
否则第二次执行就红——这是新手写接口自动化最常见的崩盘点。
"""
from __future__ import annotations

import time

import pytest

from api.user_api import UserApi


@pytest.fixture
def user_api(client) -> UserApi:
    return UserApi(client)


@pytest.fixture
def anonymous_user_api(http) -> UserApi:
    """不带 token，用于鉴权反例。"""
    return UserApi(http)


@pytest.fixture
def created_user(user_api: UserApi):
    """造一个唯一账号的用户，用例结束后删除。

    用时间戳保证唯一：并发执行或重复执行都不会因"账号已存在"而失败。
    """
    suffix = f"{int(time.time() * 1000)}"
    payload = {
        "userName": f"auto_{suffix}",
        "nickName": f"自动化临时用户_{suffix}",
        "password": "Test@123456",
        "status": "0",
        "remark": "接口自动化用例创建，请勿手工修改",
    }
    resp = user_api.add_user(payload)
    body = resp.json()
    assert body.get("code") == 200, f"前置造数失败，无法继续\n响应: {resp.text[:500]}"

    # 新增接口不返回主键，从列表里反查（真实系统就是这样，这也是一个可以提的改进点）
    listing = user_api.list_users(page_num=1, page_size=50, user_name=payload["userName"]).json()
    rows = listing.get("rows") or []
    assert rows, f"新增成功但列表中查不到，说明新增与查询存在数据不一致\n响应: {listing}"
    user_id = rows[0]["userId"]

    yield {**payload, "userId": user_id}

    user_api.delete_user(user_id)      # 后置清理，失败不影响用例结论
