"""登录 / 用户管理 接口定义。

接口签名以若依（RuoYi-Vue）为准：
  POST   /login                     登录，body: {username, password, code, uuid}
  GET    /captchaImage              验证码开关
  GET    /system/user/list          分页查询 pageNum/pageSize/userName/status
  POST   /system/user               新增
  GET    /system/user/{userId}      详情
  PUT    /system/user               修改
  DELETE /system/user/{userIds}     删除（支持逗号分隔批量）

换成别的系统时，只改这个文件。
"""
from __future__ import annotations

from typing import Any, Optional

from api.base_api import BaseApi


class LoginApi(BaseApi):
    def login(self, username: str, password: str, code: str = "", uuid: str = ""):
        return self.client.post(
            "/login",
            json={"username": username, "password": password, "code": code, "uuid": uuid},
        )

    def captcha_info(self):
        return self.client.get("/captchaImage")


class UserApi(BaseApi):
    def list_users(self, page_num: int = 1, page_size: int = 10,
                   user_name: Optional[str] = None, status: Optional[str] = None):
        params: dict[str, Any] = {"pageNum": page_num, "pageSize": page_size}
        if user_name is not None:
            params["userName"] = user_name
        if status is not None:
            params["status"] = status
        return self.client.get("/system/user/list", params=params)

    def add_user(self, payload: dict[str, Any]):
        return self.client.post("/system/user", json=payload)

    def get_user(self, user_id: int):
        return self.client.get(f"/system/user/{user_id}")

    def update_user(self, payload: dict[str, Any]):
        return self.client.put("/system/user", json=payload)

    def delete_user(self, user_ids: int | str):
        return self.client.delete(f"/system/user/{user_ids}")





class RoleApi(BaseApi):
    def list_roles(self, page_num: int = 1, page_size: int = 10,
                   role_name: Optional[str] = None, status: Optional[str] = None):
        params: dict[str, Any] = {"pageNum": page_num, "pageSize": page_size}
        if role_name is not None:
            params["roleName"] = role_name
        if status is not None:
            params["status"] = status
        return self.client.get("/system/role/list", params=params)

    def add_role(self, payload: dict[str, Any]):
        return self.client.post("/system/role", json=payload)

    def update_role(self, payload: dict[str, Any]):
        return self.client.put("/system/role", json=payload)

    def delete_role(self, role_ids: int | str):
        return self.client.delete(f"/system/role/{role_ids}")