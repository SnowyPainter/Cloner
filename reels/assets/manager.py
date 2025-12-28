from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from reels.assets.models import Asset, AssetPaths, Status
from reels.assets.registry import AssetRegistry
from reels.utils.fs import ensure_dir, read_json, write_json
from reels.utils.time import utc_now_iso


YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})")


class AssetManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("workspace")
        self.assets_root = self.root / "assets"
        self.registry = AssetRegistry(self.assets_root / "registry.json")
        ensure_dir(self.assets_root)

    def create(self, youtube_url: str) -> Asset:
        youtube_id = extract_youtube_id(youtube_url)
        existing_id = self.registry.get_asset_id(youtube_id)
        if existing_id:
            return self.get(existing_id)

        asset_id = f"YT_{youtube_id}"
        asset_root = self.assets_root / asset_id
        paths = AssetPaths.build(asset_root)

        ensure_dir(paths.source_dir)
        ensure_dir(paths.subtitles_dir)
        ensure_dir(paths.derived_dir)
        ensure_dir(paths.output_dir)

        asset = Asset(
            asset_id=asset_id,
            source="youtube",
            youtube_id=youtube_id,
            title="",
            duration=0.0,
            created_at=utc_now_iso(),
            paths=paths,
        )
        write_json(paths.asset_json, asset.to_dict())
        self.update_status(asset_id, stage="pending", status="created")
        self.registry.register(youtube_id, asset_id)
        return asset

    def get(self, asset_id: str) -> Asset:
        asset_root = self.assets_root / asset_id
        paths = AssetPaths.build(asset_root)
        data = read_json(paths.asset_json)
        return Asset.from_dict(data, paths)

    def update_status(self, asset_id: str, stage: str, status: str) -> Status:
        asset_root = self.assets_root / asset_id
        paths = AssetPaths.build(asset_root)
        state = Status(stage=stage, status=status, updated_at=utc_now_iso())
        write_json(paths.status_json, state.to_dict())
        return state

    def update_asset(self, asset: Asset) -> Asset:
        write_json(asset.paths.asset_json, asset.to_dict())
        return asset

    def list_assets(self) -> Iterable[str]:
        if not self.assets_root.exists():
            return []
        return [p.name for p in self.assets_root.iterdir() if p.is_dir()]


def extract_youtube_id(url: str) -> str:
    match = YOUTUBE_ID_RE.search(url)
    if not match:
        raise ValueError("Unsupported YouTube URL format")
    return match.group(1)
