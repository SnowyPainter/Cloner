from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict

from reels.utils.fs import ensure_dir, write_json
from reels.utils.time import utc_now_iso


def run_job(root: Path, name: str, payload: Dict[str, Any], fn: Callable[[], Dict[str, Any]]) -> Path:
    timestamp = utc_now_iso().replace(":", "").replace("-", "")
    job_dir = root / "jobs" / f"{name}_{timestamp}"
    ensure_dir(job_dir)

    write_json(job_dir / "input.json", payload)
    try:
        result = fn()
        write_json(job_dir / "result.json", result)
    except Exception as exc:
        (job_dir / "error.txt").write_text(str(exc) + "\n", encoding="utf-8")
        raise
    return job_dir
