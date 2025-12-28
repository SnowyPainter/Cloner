from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class AssetPaths:
    root: Path
    asset_json: Path
    status_json: Path
    source_dir: Path
    subtitles_dir: Path
    derived_dir: Path
    output_dir: Path
    source_video: Path
    subtitles_original: Path
    shots_json: Path
    highlight_json: Path
    output_reel: Path

    @staticmethod
    def build(root: Path) -> "AssetPaths":
        source_dir = root / "source"
        subtitles_dir = root / "subtitles"
        derived_dir = root / "derived"
        output_dir = root / "output"
        return AssetPaths(
            root=root,
            asset_json=root / "asset.json",
            status_json=root / "status.json",
            source_dir=source_dir,
            subtitles_dir=subtitles_dir,
            derived_dir=derived_dir,
            output_dir=output_dir,
            source_video=source_dir / "video.mp4",
            subtitles_original=subtitles_dir / "original.srt",
            shots_json=derived_dir / "shots.json",
            highlight_json=derived_dir / "highlight.json",
            output_reel=output_dir / "reel_60s.mp4",
        )


@dataclass
class Asset:
    asset_id: str
    source: str
    youtube_id: str
    title: str
    duration: float
    created_at: str
    paths: AssetPaths

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "source": self.source,
            "youtube_id": self.youtube_id,
            "title": self.title,
            "duration": self.duration,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], paths: AssetPaths) -> "Asset":
        return Asset(
            asset_id=data["asset_id"],
            source=data["source"],
            youtube_id=data["youtube_id"],
            title=data.get("title", ""),
            duration=float(data.get("duration", 0.0)),
            created_at=data["created_at"],
            paths=paths,
        )


@dataclass
class Status:
    stage: str
    status: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Status":
        return Status(
            stage=data["stage"],
            status=data["status"],
            updated_at=data["updated_at"],
        )
