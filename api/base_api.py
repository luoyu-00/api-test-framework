"""接口层：一个业务模块一个类，只负责"怎么发请求"，不负责"断言对不对"。

这一层存在的意义：接口地址/字段变了，只改这里，用例不用动。
"""
from __future__ import annotations

from common.http_client import HttpClient


class BaseApi:
    def __init__(self, client: HttpClient):
        self.client = client
