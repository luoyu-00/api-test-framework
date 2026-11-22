"""全局 fixture。

这里只做三件事：
  1. 把环境配置读进来（用例里不出现任何 ip / 密码）
  2. 登录一次，产出带 token 的 client（session 级，60 条用例只登录一次）
  3. 产出一个不带 token 的 client，专门测鉴权
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.user_api import LoginApi          # noqa: E402
from common.http_client import HttpClient  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default=None, help="运行环境: local / ci / staging")


@pytest.fixture(scope="session")
def config(pytestconfig) -> dict:
    env = pytestconfig.getoption("--env") or os.getenv("TEST_ENV") or "local"
    raw = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if env not in raw["envs"]:
        raise ValueError(f"config.yaml 里没有环境 '{env}'，可选: {list(raw['envs'])}")

    cfg = dict(raw["envs"][env])
    cfg["env"] = env
    cfg["timeout"] = raw.get("timeout", 10)
    cfg["token_scheme"] = raw.get("token_scheme", "Bearer")
    cfg["accounts"] = raw.get("accounts", {})
    return cfg


@pytest.fixture(scope="session")
def http(config) -> HttpClient:
    """不带 token 的客户端，用于鉴权反例。"""
    client = HttpClient(config["base_url"], config["timeout"])
    yield client
    client.close()


@pytest.fixture(scope="session")
def token(config, http) -> str:
    account = config["accounts"]["admin"]
    resp = LoginApi(http).login(account["username"], account["password"])
    body = resp.json()
    assert body.get("code") == 200 and body.get("token"), (
        f"登录失败，后续用例无法执行\n环境: {config['env']} ({config['base_url']})\n"
        f"状态码: {resp.status_code}\n响应: {resp.text[:600]}"
    )
    return body["token"]


@pytest.fixture(scope="session")
def client(config, token) -> HttpClient:
    """已登录的客户端，绝大多数用例用它。"""
    c = HttpClient(config["base_url"], config["timeout"])
    c.set_token(token, config["token_scheme"])
    yield c
    c.close()


def pytest_sessionfinish(session, exitstatus):
    """把环境信息写进 allure 报告首页（Environment 区块）。"""
    results_dir = ROOT / "allure-results"
    if not results_dir.exists():
        return
    env_option = session.config.getoption("--env") or os.getenv("TEST_ENV") or "local"
    try:
        raw = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        base_url = raw["envs"][env_option]["base_url"]
        sut = raw["envs"][env_option]["sut"]
    except Exception:
        base_url, sut = "unknown", "unknown"

    lines = [
        f"env={env_option}",
        f"base_url={base_url}",
        f"sut={sut}",
        f"python={sys.version.split()[0]}",
    ]
    (results_dir / "environment.properties").write_text("\n".join(lines), encoding="utf-8")
