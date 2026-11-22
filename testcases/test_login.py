"""登录与鉴权模块用例（13 条）。

设计说明：
  - 登录是所有业务的入口，它挂了后面全挂，所以单独一个模块、断言要严
  - 数据驱动的部分放在 data/login_data.yaml，本文件只负责"怎么验"
"""
import allure
import pytest

from api.user_api import LoginApi
from common.assert_util import (
    assert_biz_code,
    assert_http_status,
    assert_msg_contains,
    assert_not_empty,
)
from common.data_loader import case_ids, load_cases

FEATURE = "登录与鉴权"

# 只加载反例：正例和鉴权用例含较多步骤断言，写在代码里比塞进 yaml 可读性更好
NEGATIVE_CASES = load_cases("login_data.yaml", "negative")


@allure.feature(FEATURE)
@pytest.mark.login
class TestLogin:

    # ---------- 正例 ----------

    @allure.story("账号密码登录")
    @allure.title("登录成功返回可用token")
    @pytest.mark.smoke
    def test_login_success(self, http):
        with allure.step("使用管理员账号登录"):
            resp = LoginApi(http).login("admin", "admin123")

        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        with allure.step("校验返回了 token"):
            token = assert_not_empty(resp, "token")
            assert isinstance(token, str) and len(token) > 10, f"token 格式异常: {token!r}"

    @allure.story("验证码开关")
    @allure.title("查询验证码配置返回开关状态")
    def test_captcha_config(self, http):
        resp = LoginApi(http).captcha_info()
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        with allure.step("校验 captchaEnabled 字段存在"):
            assert "captchaEnabled" in resp.json(), f"响应缺少 captchaEnabled 字段: {resp.text[:300]}"

    # ---------- 反例（数据驱动） ----------

    @allure.story("账号密码登录")
    @pytest.mark.parametrize("case", NEGATIVE_CASES, ids=case_ids(NEGATIVE_CASES))
    def test_login_negative(self, http, case):
        allure.dynamic.title(case["title"])
        if case.get("note"):
            allure.dynamic.description(case["note"])

        with allure.step(f"使用账号 {case['username']!r} 登录"):
            resp = LoginApi(http).login(case["username"], case["password"])

        assert_http_status(resp, 200)                 # 业务失败也是 HTTP 200
        assert_biz_code(resp, case["expected_code"])
        if case.get("expected_msg"):
            assert_msg_contains(resp, case["expected_msg"])

    # ---------- 边界 ----------

    @allure.story("边界值")
    @allure.title("用户名/密码最小长度边界")
    @pytest.mark.boundary
    @pytest.mark.parametrize("username,password", [("a", "admin123"), ("admin", "1")])
    def test_login_min_length_boundary(self, http, username, password):
        resp = LoginApi(http).login(username, password)
        assert_http_status(resp, 200)
        assert_biz_code(resp, 500)

    # ---------- 鉴权 ----------

    @allure.story("鉴权")
    @allure.title("未携带token访问受保护接口返回401")
    @pytest.mark.smoke
    def test_no_token_returns_401(self, http):
        resp = http.get("/system/user/list", params={"pageNum": 1, "pageSize": 10})
        assert_http_status(resp, 401)
        with allure.step("校验返回了明确的未认证提示"):
            assert "认证" in resp.text or "token" in resp.text.lower(), f"401 但提示信息不明确: {resp.text[:300]}"

    @allure.story("鉴权")
    @allure.title("携带伪造token访问受保护接口返回401")
    def test_fake_token_returns_401(self, http):
        resp = http.get(
            "/system/user/list",
            params={"pageNum": 1, "pageSize": 10},
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fake.signature"},
        )
        assert_http_status(resp, 401)
