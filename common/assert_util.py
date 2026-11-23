"""断言封装。

不使用裸 assert 的原因：
  裸 assert 失败时只给出 False != True，必须重跑才能定位问题。
  这里的每个断言都把「预期 / 实际 / 响应全文」写进失败信息，并落到 allure 步骤里。
"""
from __future__ import annotations

from typing import Any

import requests

try:
    import allure
except ImportError:
    allure = None


class _Step:
    """没装 allure 时退化成空上下文。"""

    def __init__(self, title: str):
        self.title = title
        self._ctx = allure.step(title) if allure else None

    def __enter__(self):
        if self._ctx:
            self._ctx.__enter__()
        return self

    def __exit__(self, *exc):
        if self._ctx:
            return self._ctx.__exit__(*exc)
        return False


def _brief(resp: requests.Response, limit: int = 600) -> str:
    text = resp.text or ""
    return text[:limit] + ("..." if len(text) > limit else "")


def assert_http_status(resp: requests.Response, expected: int = 200) -> None:
    with _Step(f"校验 HTTP 状态码 == {expected}"):
        assert resp.status_code == expected, (
            f"HTTP 状态码不符\n预期: {expected}\n实际: {resp.status_code}\n"
            f"URL: {resp.url}\n响应: {_brief(resp)}"
        )


def assert_biz_code(resp: requests.Response, expected: int = 200) -> None:
    """校验业务码（若依体系里 HTTP 200 也可能 code=500）。"""
    with _Step(f"校验业务码 code == {expected}"):
        try:
            body = resp.json()
        except ValueError:
            raise AssertionError(f"响应不是合法 JSON，无法校验业务码\nURL: {resp.url}\n响应: {_brief(resp)}")
        assert body.get("code") == expected, (
            f"业务码不符\n预期: {expected}\n实际: {body.get('code')}\n"
            f"msg: {body.get('msg')}\nURL: {resp.url}\n响应: {_brief(resp)}"
        )


def assert_msg_contains(resp: requests.Response, expected: str) -> None:
    with _Step(f"校验提示信息包含「{expected}」"):
        body = resp.json()
        msg = str(body.get("msg", ""))
        assert expected in msg, f"提示信息不符\n预期包含: {expected}\n实际: {msg}\n响应: {_brief(resp)}"


def assert_not_empty(resp: requests.Response, key: str = "data") -> Any:
    with _Step(f"校验字段 {key} 非空"):
        body = resp.json()
        value = body.get(key)
        assert value, f"字段 {key} 为空\n响应: {_brief(resp)}"
        return value


def assert_field(resp: requests.Response, path: str, expected: Any) -> None:
    """按 a.b.c 路径取嵌套字段比对，例如 assert_field(resp, "data.userName", "admin")。"""
    with _Step(f"校验字段 {path} == {expected!r}"):
        node: Any = resp.json()
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                raise AssertionError(f"响应里找不到路径 {path}（断在 {part}）\n响应: {_brief(resp)}")
            node = node[part]
        assert node == expected, f"字段值不符\n路径: {path}\n预期: {expected!r}\n实际: {node!r}"


def assert_schema(resp: requests.Response, required_keys: list[str]) -> None:
    """轻量契约校验：只查字段是否存在，不做全字段比对（避免接口加字段就红）。"""
    with _Step(f"校验响应包含字段 {required_keys}"):
        body = resp.json()
        missing = [k for k in required_keys if k not in body]
        assert not missing, f"响应缺少字段: {missing}\n响应: {_brief(resp)}"
