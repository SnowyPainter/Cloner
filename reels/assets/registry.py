from __future__ import annotations

from pathlib import Path
from typing import Dict

from reels.utils.fs import read_json, write_json


class AssetRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}
        return read_json(self.path)

    def save(self, data: Dict[str, str]) -> None:
        write_json(self.path, data)

    def get_asset_id(self, youtube_id: str) -> str | None:
        data = self.load()
        return data.get(youtube_id)

    def register(self, youtube_id: str, asset_id: str) -> None:
        data = self.load()
        data[youtube_id] = asset_id
        self.save(data)
