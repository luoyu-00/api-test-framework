"""角色管理模块用例（12 条）。

覆盖正例、反例、边界与鉴权，重点验证：
    新增 -> 列表可查 -> 修改 -> 再查已变 -> 删除 -> 确认查不到
"""
import time
import allure
import pytest

from api.user_api import RoleApi
from common.assert_util import (
    assert_biz_code,
    assert_field,
    assert_http_status,
    assert_msg_contains,
)

FEATURE = "角色管理"


@allure.feature(FEATURE)
@pytest.mark.role
class TestRoleQuery:

    @allure.story("查询角色列表")
    @allure.title("分页查询角色列表默认返回第一页")
    @pytest.mark.smoke
    def test_list_default_page(self, role_api: RoleApi):
        resp = role_api.list_roles()
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        with allure.step("校验分页结构完整且非空"):
            body = resp.json()
            assert "rows" in body and "total" in body, f"分页响应结构不完整: {resp.text[:300]}"
            assert isinstance(body["rows"], list)
            assert body["total"] >= 1, "默认角色列表不应为空"

    @allure.story("查询角色列表")
    @allure.title("按角色名称精确过滤")
    def test_list_filter_by_role_name(self, role_api: RoleApi, created_role):
        resp = role_api.list_roles(role_name=created_role["roleName"])
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] >= 1, f"按唯一角色名查询应至少命中1条，实际 {body['total']}"
        assert body["rows"][0]["roleName"] == created_role["roleName"]

    @allure.story("查询角色列表")
    @allure.title("按不存在的角色名过滤返回空列表")
    def test_list_filter_not_exist(self, role_api: RoleApi):
        resp = role_api.list_roles(role_name="no_such_role_zzz_999")
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] == 0
        assert body["rows"] == []

    @allure.story("分页边界")
    @allure.title("pageSize=1 只返回 1 条")
    @pytest.mark.boundary
    def test_page_size_one(self, role_api: RoleApi):
        resp = role_api.list_roles(page_num=1, page_size=1)
        assert_biz_code(resp, 200)
        rows = resp.json()["rows"]
        assert len(rows) == 1, f"pageSize=1 应返回1条，实际 {len(rows)}"

    @allure.story("分页边界")
    @allure.title("pageNum=0 的处理")
    @pytest.mark.boundary
    def test_page_num_zero(self, role_api: RoleApi):
        """边界用例：记录服务端对 pageNum=0 的处理行为"""
        resp = role_api.list_roles(page_num=0, page_size=10)
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        # 被测服务实现：start = max(0, (0-1)*10) = 0，返回第一页
        with allure.step("断言服务端容错处理，未发生崩溃，且返回了数据"):
            assert len(resp.json()["rows"]) > 0, "pageNum=0 时服务端未返回数据或处理异常"

    @allure.story("分页边界")
    @allure.title("pageSize=0 返回空列表但 total 仍为真实总数")
    @pytest.mark.boundary
    def test_page_size_zero(self, role_api: RoleApi):
        """pageSize=0 是最容易被写崩的参数（除零/负索引）。这里验两件事：
        不抛 500，且 total 仍是全量数——分页参数只影响本页数据，不影响总数。
        """
        normal = role_api.list_roles().json()
        resp = role_api.list_roles(page_size=0)
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] == normal["total"], (
            f"pageSize=0 时 total 被改动了\n预期: {normal['total']}\n实际: {body['total']}"
        )
        assert body["rows"] == [], f"pageSize=0 应返回空列表，实际 {len(body['rows'])} 条"

    @allure.story("查询角色列表")
    @allure.title("[已知缺陷 BUG-01] status 过滤参数未生效，结果等于全量")
    def test_list_filter_by_status_not_effective(self, role_api: RoleApi):
        """缺陷记录型用例（characterization test）。

        现象：/system/role/list 未实现 status 过滤，传 status=9（不存在的状态）
              仍返回全部角色。对照若依原版接口，该参数是生效的。

        写法说明：这里按「当前实际行为」断言，目的是防回归，不是为了通过。
              缺陷修复后，本用例会变红——那时把断言改成 total == 0 即可。
        """
        all_rows = role_api.list_roles().json()
        resp = role_api.list_roles(status="9")
        assert_biz_code(resp, 200)
        body = resp.json()
        assert body["total"] == all_rows["total"], (
            f"status 过滤似乎已生效（total 从 {all_rows['total']} 变成 {body['total']}）。\n"
            f"若缺陷已修复，请把本用例断言改为 total == 0 并移除 BUG-01 标记。\n"
            f"响应: {resp.text[:300]}"
        )


@allure.feature(FEATURE)
@pytest.mark.role
class TestRoleWrite:

    @allure.story("新增角色")
    @allure.title("新增合法角色成功且列表可查")
    @pytest.mark.smoke
    def test_add_then_list(self, role_api: RoleApi):
        role_name = f"auto_role_{int(time.time() * 1000)}"
        role_key = f"auto_key_{int(time.time() * 1000)}"
        payload = {"roleName": role_name, "roleKey": role_key, "status": "0"}

        resp = role_api.add_role(payload)
        assert_biz_code(resp, 200)

        with allure.step("写入后立即查询，验证数据已落库"):
            listing = role_api.list_roles(role_name=role_name).json()
            assert listing["total"] == 1, f"新增成功但查不到，total={listing['total']}"
            role_id = listing["rows"][0]["roleId"]

        with allure.step("清理测试数据"):
            role_api.delete_role(role_id)

    @allure.story("新增角色")
    @allure.title("新增重复 roleKey 失败")
    def test_add_duplicate_role_key(self, role_api: RoleApi, created_role):
        payload = {
            "roleName": "重复权限字符角色",
            "roleKey": created_role["roleKey"],  # 使用已存在的 key
            "status": "0",
        }
        resp = role_api.add_role(payload)
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "已存在")

    @allure.story("新增角色")
    @allure.title("新增缺少 roleName 失败")
    def test_add_without_role_name(self, role_api: RoleApi):
        # SUT 中判断了 if not role_name or not role_key
        resp = role_api.add_role({"roleKey": "no_name_key"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "不能为空")

    @allure.story("新增角色")
    @allure.title("roleName 超长（31 字符）")
    @pytest.mark.boundary
    def test_add_role_name_too_long(self, role_api: RoleApi):
        """边界用例：观察实际行为。SUT 目前未对 roleName 做长度限制，预期为 200 成功"""
        role_name = "a" * 31
        role_key = f"key_long_{int(time.time() * 1000)}"
        resp = role_api.add_role({"roleName": role_name, "roleKey": role_key})

        # 当前契约对角色名长度不设上限，此处记录实际行为；若后续加入限制，该断言会失败并提示更新预期
        assert_biz_code(resp, 200)

        with allure.step("清理超长名字角色"):
            if resp.json()["code"] == 200:
                listing = role_api.list_roles(role_name=role_name).json()
                if listing["total"] > 0:
                    role_api.delete_role(listing["rows"][0]["roleId"])

    @allure.story("修改角色")
    @allure.title("修改角色名称后详情已变")
    def test_update_role_name(self, role_api: RoleApi, created_role):
        new_name = created_role["roleName"] + "_已修改"
        payload = {
            "roleId": created_role["roleId"],
            "roleName": new_name,
        }

        assert_biz_code(role_api.update_role(payload), 200)

        with allure.step("重新查询确认修改已生效"):
            # 注意：SUT 的 Role 没有写单条详情 GET 接口，所以用 list 过滤来查
            listing = role_api.list_roles(role_name=new_name).json()
            assert listing["total"] == 1
            assert listing["rows"][0]["roleId"] == created_role["roleId"]

    @allure.story("删除角色")
    @allure.title("删除自己造的角色后列表查不到")
    def test_delete_then_query(self, role_api: RoleApi):
        role_name = f"auto_del_role_{int(time.time() * 1000)}"
        role_key = f"auto_del_key_{int(time.time() * 1000)}"
        role_api.add_role({"roleName": role_name, "roleKey": role_key})

        role_id = role_api.list_roles(role_name=role_name).json()["rows"][0]["roleId"]
        assert_biz_code(role_api.delete_role(role_id), 200)

        with allure.step("删除后查询，确认数据已消失"):
            listing = role_api.list_roles(role_name=role_name).json()
            assert listing["total"] == 0, f"删除后仍能查到，total={listing['total']}"

    @allure.story("鉴权")
    @allure.title("无 token 访问角色列表返回 401")
    def test_query_without_token(self, anonymous_role_api: RoleApi):
        resp = anonymous_role_api.list_roles()
        assert_http_status(resp, 401)

    # ---------- Day6 补充 ----------

    @allure.story("删除角色")
    @allure.title("删除不存在的角色返回成功（幂等）")
    def test_delete_not_exist_idempotent(self, role_api: RoleApi):
        """幂等性：重复删除不存在的资源，不该报错——否则重试机制会误报失败。"""
        resp = role_api.delete_role(99999)
        assert_http_status(resp, 200)
        assert_biz_code(resp, 200)

    @allure.story("删除角色")
    @allure.title("删除超级管理员角色被拒绝")
    def test_delete_admin_role_forbidden(self, role_api: RoleApi):
        resp = role_api.delete_role(1)
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "不允许")

    @allure.story("修改角色")
    @allure.title("缺少 roleId 修改失败")
    def test_update_without_role_id(self, role_api: RoleApi):
        resp = role_api.update_role({"roleName": "没有主键的角色"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "角色ID不能为空")

    @allure.story("修改角色")
    @allure.title("修改不存在的角色失败")
    def test_update_not_exist_role(self, role_api: RoleApi):
        resp = role_api.update_role({"roleId": 99999, "roleName": "幽灵角色"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "角色不存在")

    @allure.story("修改角色")
    @allure.title("把 roleKey 改成已存在的值失败")
    def test_update_duplicate_role_key(self, role_api: RoleApi, created_role):
        """唯一键冲突同样要在「修改」路径校验，只测新增是常见漏测点。"""
        resp = role_api.update_role({"roleId": created_role["roleId"], "roleKey": "admin"})
        assert_biz_code(resp, 500)
        assert_msg_contains(resp, "已存在")

    @allure.story("删除角色")
    @allure.title("批量删除两个角色后均查不到")
    def test_delete_batch(self, role_api: RoleApi):
        """逗号分隔批量删除：单删通过不代表批量通过（拆分逻辑是另一段代码）。"""
        stamp = int(time.time() * 1000)
        names = [f"批删{n}{stamp}" for n in ("A", "B")]
        ids = []
        for n in names:
            assert_biz_code(role_api.add_role({"roleName": n, "roleKey": f"bk{n}{stamp}"}), 200)
            ids.append(role_api.list_roles(role_name=n).json()["rows"][0]["roleId"])

        assert_biz_code(role_api.delete_role(f"{ids[0]},{ids[1]}"), 200)
        with allure.step("两个角色都应查不到"):
            for n in names:
                assert role_api.list_roles(role_name=n).json()["total"] == 0, f"{n} 未被删除"

