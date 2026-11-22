"""日志：同时输出到控制台和 logs/run.log。

为什么要两个通道：
  - 控制台：跑用例时实时看
  - 文件：CI 失败后事后追查，不用重跑
"""
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_FMT = "%(asctime)s | %(levelname)-7s | %(name)-10s | %(message)s"
_DATEFMT = "%H:%M:%S"


def get_logger(name: str = "api-test") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # 避免重复添加 handler 导致日志打印两遍
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


log = get_logger()
