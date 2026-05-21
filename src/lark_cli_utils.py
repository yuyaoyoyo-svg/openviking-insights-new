#!/usr/bin/env python3
"""
Utilities for running lark-cli in both local and CI environments.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def get_lark_identity() -> str:
    return os.getenv("LARK_IDENTITY", "auto").strip() or "auto"


def is_ci() -> bool:
    return os.getenv("GITHUB_ACTIONS", "").lower() == "true" or os.getenv("CI", "").lower() == "true"


def should_write_env_file() -> bool:
    if os.getenv("WRITE_ENV_UPDATES", "").lower() in {"1", "true", "yes"}:
        return True
    if os.getenv("DISABLE_ENV_FILE_WRITE", "").lower() in {"1", "true", "yes"}:
        return False
    return not is_ci()


def ensure_lark_cli_ready() -> bool:
    try:
        version = subprocess.run(
            ["lark-cli", "--version"], capture_output=True, text=True, timeout=15
        )
    except FileNotFoundError:
        return False
    except Exception:
        return False

    if version.returncode != 0:
        return False

    identity = get_lark_identity()
    if identity == "user":
        status = subprocess.run(
            ["lark-cli", "auth", "status"], capture_output=True, text=True, timeout=30
        )
        return status.returncode == 0

    return True


def lark_base_cmd(subcommand: str, *, base_token: str | None = None, table_id: str | None = None) -> list[str]:
    cmd = ["lark-cli", "base", subcommand]
    if base_token:
        cmd.extend(["--base-token", base_token])
    if table_id:
        cmd.extend(["--table-id", table_id])
    cmd.extend(["--as", get_lark_identity()])
    return cmd


def run_lark_json(cmd: list[str], timeout: int = 120) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def update_env_file_var(env_path: Path, key: str, value: str) -> bool:
    if not should_write_env_file():
        return False

    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[idx] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
