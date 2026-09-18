"""从项目根目录的 `.env` 加载密钥，已存在的环境变量不会被覆盖。

`.env` 已加入 .gitignore，不会进仓库。GitHub Actions 继续用 Secrets。
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import PACKAGE_ROOT


def load_dotenv(path: str | Path | None = None) -> Path | None:
    candidate = Path(path) if path else PACKAGE_ROOT / ".env"
    if not candidate.is_file():
        return None
    for raw in candidate.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value
    return candidate
