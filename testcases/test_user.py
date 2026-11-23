"""用户管理模块用例（15 条）。

这一组用例的价值在于演示「完整业务闭环」：
    新增 → 列表可查 → 详情正确 → 修改 → 再查已变 → 删除 → 确认查不到

单看 code==200 不叫测试，叫可用性探测。真正的测试要验证「状态确实发生了改变」。
"""
import time

import allure
import pytest

from api.user_api import UserApi
from common.assert_util import (
    assert_biz_code,
    assert_field,
    assert_http_status,
    assert_msg_contains,
    assert_not_empty,
)

FEATURE = "用户管理"


@allure.feature(FEATURE)
@pytest.mark.user
class TestUserQuery:

    @allure.story("查询用户列表")
    @allure.title("默认分页查询返回列表与总数")
    @pytest.mark.smoke
    def test_list_default_page(self, user_api: UserApi):
        resp = user_api.list_users()
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        with allure.step("校验分页结构完整"):
            body = resp.json()
            assert "rows" in body and "total" in body, f"分页响应结构不完整: {resp.text[:300]}"
            assert isinstance(body["rows"], list)

    @allure.story("查询用户列表")
    @allure.title("按用户名精确查询命中1条")
    def test_list_filter_by_username(self, user_api: UserApi, created_user):
        resp = user_api.list_users(user_name=created_user["userName"])
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] >= 1, f"按唯一用户名查询应至少命中1条，实际 {body['total']}"
        assert body["rows"][0]["userName"] == created_user["userName"]

    @allure.story("查询用户列表")
    @allure.title("查询不存在的用户名返回空列表而非报错")
    def test_list_filter_not_exist(self, user_api: UserApi):
        resp = user_api.list_users(user_name="no_such_user_zzz_000")
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] == 0, f"不存在的用户名应返回0条，实际 {body['total']}"
        assert body["rows"] == []

    @allure.story("分页边界")
    @allure.title("pageSize=1时只返回1条")
    @pytest.mark.boundary
    def test_page_size_one(self, user_api: UserApi):
        resp = user_api.list_users(page_num=1, page_size=1)
        assert_biz_code(resp, 200)
        rows = resp.json()["rows"]
        assert len(rows) == 1, f"pageSize=1 应返回1条，实际 {len(rows)}"

    @allure.story("分页边界")
    @allure.title("页码超出总页数返回空列表")
    @pytest.mark.boundary
    def test_page_num_out_of_range(self, user_api: UserApi):
        resp = user_api.list_users(page_num=9999, page_size=10)
        assert_biz_code(resp, 200)
        assert resp.json()["rows"] == [], "页码越界应返回空列表，实际返回了数据"

    @allure.story("分页边界")
    @allure.title("页码为0时服务端不返回500")
    @pytest.mark.boundary
    def test_page_num_zero(self, user_api: UserApi):
        """这条是典型的"防御性用例"：非法入参不应导致服务端异常。"""
        resp = user_api.list_users(page_num=0, page_size=10)
        assert_http_status(resp, 200)
        assert resp.status_code != 500, "页码为0导致服务端异常，属于入参校验缺失"

    @allure.story("查询用户详情")
    @allure.title("按ID查询返回正确的用户名")
    def test_get_user_detail(self, user_api: UserApi, created_user):
        resp = user_api.get_user(created_user["userId"])
        assert_biz_code(resp, 200)
        assert_field(resp, "data.userName", created_user["userName"])

    @allure.story("查询用户详情")
    @allure.title("查询不存在的用户ID返回失败且不抛500")
    def test_get_user_not_exist(self, user_api: UserApi):
        resp = user_api.get_user(99999999)
        with allure.step("校验服务端未崩溃"):
            assert resp.status_code != 500, f"查询不存在ID导致服务端异常: {resp.text[:300]}"

    @allure.story("鉴权")
    @allure.title("未登录用户无法查询用户列表")
    def test_query_without_token(self, anonymous_user_api: UserApi):
        resp = anonymous_user_api.list_users()
        assert_http_status(resp, 401)

    @allure.story("查询用户列表")
    @allure.title("按状态过滤只返回该状态的用户")
    def test_list_filter_by_status(self, user_api: UserApi):
        """造一个 status=1 的用户，再按 status=1 查，校验「每一行」都符合，而不只看 total。"""
        name = f"status1_{int(time.time() * 1000)}"
        assert_biz_code(user_api.add_user({"userName": name, "status": "1"}), 200)
        user_id = user_api.list_users(user_name=name).json()["rows"][0]["userId"]
        try:
            resp = user_api.list_users(status="1", page_size=50)
            assert_biz_code(resp, 200)
            body = resp.json()
            assert body["total"] >= 1, f"存在 status=1 的用户，但过滤结果为空: {resp.text[:300]}"
            mismatched = [r for r in body["rows"] if r.get("status") != "1"]
            assert not mismatched, f"状态过滤失效，结果里混入非 1 状态的行: {mismatched[:3]}"
        finally:
            user_api.delete_user(user_id)


@allure.feature(FEATURE)
@pytest.mark.user
class TestUserWrite:

    @allure.story("新增用户")
    @allure.title("新增用户后列表可查到（写后读一致性）")
    @pytest.mark.smoke
    def test_add_then_list(self, user_api: UserApi):
        import time
        username = f"auto_add_{int(time.time() * 1000)}"
        payload = {"userName": username, "nickName": "新增校验用户", "password": "Test@123456", "status": "0"}

        resp = user_api.add_user(payload)
        assert_biz_code(resp, 200)

        with allure.step("写入后立即查询，验证数据已落库"):
            listing = user_api.list_users(user_name=username).json()
            assert listing["total"] == 1, f"新增成功但查不到（写后读不一致），total={listing['total']}"
            user_id = listing["rows"][0]["userId"]

        with allure.step("清理测试数据"):
            user_api.delete_user(user_id)

    @allure.story("新增用户")
    @allure.title("新增重复账号被拒绝")
    def test_add_duplicate_username(self, user_api: UserApi, created_user):
        payload = {
            "userName": created_user["userName"],
            "nickName": "重复账号",
            "password": "Test@123456",
            "status": "0",
        }
        resp = user_api.add_user(payload)
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "已存在")

    @allure.story("新增用户")
    @allure.title("新增缺少用户名的用户被拒绝")
    def test_add_without_username(self, user_api: UserApi):
        resp = user_api.add_user({"nickName": "无账号用户", "password": "Test@123456"})
        assert_biz_code(resp, 500)

    @allure.story("新增用户")
    @allure.title("用户名超长（31字符，超上限1位）被拒绝")
    @pytest.mark.boundary
    def test_add_username_too_long(self, user_api: UserApi):
        # 上限是 30，取 31 才是「刚好越界」；写 65 也能过，但测的是同一个判断分支，
        # 精度却低得多。边界值要贴着边界写。
        resp = user_api.add_user({
            "userName": "a" * 31,
            "nickName": "超长账号",
            "password": "Test@123456",
        })
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "30")

    @allure.story("修改用户")
    @allure.title("修改昵称后详情同步更新")
    def test_update_nickname(self, user_api: UserApi, created_user):
        new_nick = created_user["nickName"] + "_已修改"
        payload = {
            "userId": created_user["userId"],
            "userName": created_user["userName"],
            "nickName": new_nick,
        }

        assert_biz_code(user_api.update_user(payload), 200)

        with allure.step("重新查询确认修改已生效"):
            resp = user_api.get_user(created_user["userId"])
            assert_field(resp, "data.nickName", new_nick)

    @allure.story("删除用户")
    @allure.title("删除用户后列表中不再出现")
    def test_delete_then_query(self, user_api: UserApi):
        import time
        username = f"auto_del_{int(time.time() * 1000)}"
        user_api.add_user({"userName": username, "nickName": "待删除用户", "password": "Test@123456"})
        user_id = user_api.list_users(user_name=username).json()["rows"][0]["userId"]

        assert_biz_code(user_api.delete_user(user_id), 200)

        with allure.step("删除后查询，确认数据已消失"):
            listing = user_api.list_users(user_name=username).json()
            assert listing["total"] == 0, f"删除后仍能查到，total={listing['total']}"

    @allure.story("删除用户")
    @allure.title("不允许删除超级管理员账号")
    def test_delete_admin_forbidden(self, user_api: UserApi):
        """业务规则类用例：验证接口行为是否符合业务约束，而不只是通不通。"""
        resp = user_api.delete_user(1)
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "超级管理员")

    # ---------- Day6 补充 ----------

    @allure.story("修改用户")
    @allure.title("修改状态后详情同步变更")
    def test_update_status_effective(self, user_api: UserApi, created_user):
        """写后读：改完必须从详情接口读回来，只看 code==200 无法证明真的改了。"""
        user_id = created_user["userId"]
        assert_biz_code(user_api.update_user({"userId": user_id, "status": "1"}), 200)
        with allure.step("读回详情，确认 status 已变为 1"):
            assert_field(user_api.get_user(user_id), "data.status", "1")

    @allure.story("修改用户")
    @allure.title("缺少 userId 修改失败")
    def test_update_without_user_id(self, user_api: UserApi):
        resp = user_api.update_user({"nickName": "没有主键的修改"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "用户ID不能为空")

    @allure.story("修改用户")
    @allure.title("修改不存在的用户失败")
    def test_update_not_exist_user(self, user_api: UserApi):
        resp = user_api.update_user({"userId": 99999, "nickName": "幽灵用户"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "用户不存在")

    @allure.story("修改用户")
    @allure.title("把用户名改成已存在的账号失败")
    def test_update_duplicate_username(self, user_api: UserApi, created_user):
        resp = user_api.update_user({"userId": created_user["userId"], "userName": "admin"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "已存在")

    @allure.story("新增用户")
    @allure.title("用户名恰好 30 字符可以创建")
    @pytest.mark.boundary
    def test_add_username_exact_30(self, user_api: UserApi):
        """边界内：上限 30，写 30 必须成功。与「31 字符必须失败」配对才构成完整边界。"""
        name = ("b30_" + str(int(time.time() * 1000))).ljust(30, "x")[:30]
        assert len(name) == 30
        resp = user_api.add_user({"userName": name, "nickName": "边界值30"})
        assert_biz_code(resp, 200)
        with allure.step("清理边界数据"):
            rows = user_api.list_users(user_name=name).json()["rows"]
            if rows:
                user_api.delete_user(rows[0]["userId"])

    @allure.story("新增用户")
    @allure.title("不传 status 时默认可用状态为 0")
    def test_add_default_status(self, user_api: UserApi):
        """默认值也是需求的一部分：不传状态不该变成空或者 2。"""
        name = f"defstat_{int(time.time() * 1000)}"
        assert_biz_code(user_api.add_user({"userName": name}), 200)
        user_id = user_api.list_users(user_name=name).json()["rows"][0]["userId"]
        try:
            assert_field(user_api.get_user(user_id), "data.status", "0")
        finally:
            user_api.delete_user(user_id)

    @allure.story("删除用户")
    @allure.title("批量删除两个用户后均查不到")
    def test_delete_batch_users(self, user_api: UserApi):
        """逗号分隔批量删除是若依的既有能力，单删通过不代表批量通过。"""
        stamp = int(time.time() * 1000)
        names = [f"batch_{n}_{stamp}" for n in ("a", "b")]
        ids = []
        for n in names:
            assert_biz_code(user_api.add_user({"userName": n}), 200)
            ids.append(user_api.list_users(user_name=n).json()["rows"][0]["userId"])

        assert_biz_code(user_api.delete_user(f"{ids[0]},{ids[1]}"), 200)
        with allure.step("两个账号都应查不到"):
            for n in names:
                assert user_api.list_users(user_name=n).json()["total"] == 0, f"{n} 未被删除"

