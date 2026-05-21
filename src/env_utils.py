#!/usr/bin/env python3
"""
简单的 .env 加载工具，避免额外依赖。
"""

import os
from pathlib import Path


def load_env_file(env_path: Path | None = None) -> Path:
    """从项目根目录加载 .env 到环境变量。"""
    if env_path is None:
        env_path = Path(__file__).resolve().parent.parent / ".env"

    if not env_path.exists():
        return env_path

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        # Populate from .env when missing OR present-but-empty.
        if key not in os.environ or os.environ.get(key, "") == "":
            os.environ[key] = value

    return env_path
