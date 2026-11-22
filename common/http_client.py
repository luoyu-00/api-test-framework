"""HTTP 客户端封装。

封装了四件事，每一件都是接口自动化的必备工程能力：
  1. 鉴权注入     —— token 只在一处设置，用例里看不到 header
  2. 失败重试     —— 只对 5xx 和连接异常重试，不对断言失败重试
  3. 全链路日志   —— 请求/响应/耗时都记录下来，失败不用重跑就能定位
  4. 敏感脱敏     —— password/token 进日志前打码

为什么不让用例直接调 requests：
  用例里出现 headers={"Authorization": ...} 的那一天，就是框架开始腐烂的那一天。
"""
from __future__ import annotations

import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.logger import get_logger

try:
    import allure
except ImportError:          # 没装 allure 也能跑，只是没有附件
    allure = None

log = get_logger("http")

# 这些字段进日志前要打码
_SENSITIVE = {"password", "token", "authorization", "oldpassword", "newpassword", "secret"}
_MAX_LOG_BODY = 2000         # 响应体日志截断长度，避免列表接口刷屏


def _mask(data: Any) -> Any:
    """递归给敏感字段打码。"""
    if isinstance(data, dict):
        return {
            k: ("******" if str(k).lower() in _SENSITIVE else _mask(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask(i) for i in data]
    return data


def _truncate(text: str, limit: int = _MAX_LOG_BODY) -> str:
    return text if len(text) <= limit else f"{text[:limit]}...(已截断，共 {len(text)} 字符)"


class HttpClient:
    """一个会话复用连接的 HTTP 客户端。"""

    def __init__(self, base_url: str, timeout: int = 10, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        })

        # 只对连接级错误和 5xx 重试。断言失败绝不重试——那会把真 bug 掩盖成"重跑就好了"
        retry = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ---------- 鉴权 ----------

    def set_token(self, token: Optional[str], scheme: str = "Bearer") -> None:
        if token:
            self.session.headers["Authorization"] = f"{scheme} {token}"
        else:
            self.session.headers.pop("Authorization", None)

    # ---------- 核心请求 ----------

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        method = method.upper()
        kwargs.setdefault("timeout", self.timeout)

        masked_body = _mask(kwargs.get("json") or kwargs.get("data"))
        log.info("--> %s %s | params=%s | body=%s", method, url, kwargs.get("params"), masked_body)

        start = time.perf_counter()
        resp = self.session.request(method, url, **kwargs)
        cost_ms = (time.perf_counter() - start) * 1000

        log.info("<-- %s %s | %.1fms", resp.status_code, url, cost_ms)
        try:
            log.info("    resp: %s", _truncate(resp.text))
        except Exception:                      # 二进制响应等
            log.info("    resp: <binary, %d bytes>", len(resp.content))

        self._attach(method, path, masked_body, resp, cost_ms)
        return resp

    def _attach(self, method: str, path: str, body: Any, resp: requests.Response, cost_ms: float) -> None:
        """把请求响应挂到 allure 报告里，失败时能直接看到现场。"""
        if allure is None:
            return
        detail = (
            f"{method} {path}\n"
            f"耗时: {cost_ms:.1f}ms\n"
            f"请求体: {body}\n"
            f"状态码: {resp.status_code}\n"
            f"响应体:\n{_truncate(resp.text, 3000)}"
        )
        try:
            allure.attach(detail, name=f"{method} {path}", attachment_type=allure.attachment_type.TEXT)
        except Exception:
            pass

    # ---------- 语义化方法 ----------

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def close(self) -> None:
        self.session.close()
