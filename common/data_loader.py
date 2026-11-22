"""YAML 数据驱动：用例数据与用例代码分离。

好处：加一条反例用例 = 在 yaml 里加 5 行，不用改 Python。
这是测试岗面试里"数据驱动"这个说法唯一的说服方式。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_yaml(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_cases(filename: str, section: str) -> list[dict[str, Any]]:
    data = load_yaml(filename)
    cases = data.get(section)
    if not cases:
        raise KeyError(f"{filename} 里没有 '{section}' 节点，或该节点为空")
    for index, case in enumerate(cases, start=1):
        case.setdefault("title", f"{section}-第{index}条")
    return cases


def case_ids(cases: list[dict[str, Any]]) -> list[str]:
    """用 title 做 pytest 的用例 id，报告里可读，而不是 test_login[case3]。"""
    return [str(c.get("title", f"case-{i}")) for i, c in enumerate(cases)]
