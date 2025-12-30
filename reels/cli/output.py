from __future__ import annotations

from typing import Any, Mapping, TypedDict

import typer

try:
    import orjson

    def _dumps(payload: Mapping[str, Any]) -> str:
        return orjson.dumps(payload).decode("utf-8")
except Exception:  # pragma: no cover - fallback only
    import json

    def _dumps(payload: Mapping[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class IngestOutput(TypedDict):
    schema: str
    asset_id: str


class BuildOutput(TypedDict):
    schema: str
    asset_id: str
    output_path: str


def emit(payload: Mapping[str, Any]) -> None:
    typer.echo(_dumps(payload))
