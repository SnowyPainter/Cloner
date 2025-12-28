from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import orjson

    def _dumps(obj: Any) -> str:
        return orjson.dumps(obj).decode("utf-8")

    def _loads(data: str) -> Any:
        return orjson.loads(data)
except Exception:  # pragma: no cover - fallback only
    import json

    def _dumps(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def _loads(data: str) -> Any:
        return json.loads(data)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    return _loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(_dumps(data) + "\n", encoding="utf-8")
