from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reels.assets import AssetManager
from reels.subtitles import build_ass_from_srt, load_style
from reels.utils.fs import read_json, write_json
from reels.video.highlight import select
from reels.video.letterbox import detect_letterbox_crop
from reels.video.render import render_reel
from reels.video.shot_detect import detect_shots


def build(
    asset_id: str,
    workspace: Optional[Path] = None,
    style_id: str = "reels_default",
    title: Optional[str] = None,
    tagline: Optional[str] = None,
    watermark: Optional[str] = None,
) -> Path:
    manager = AssetManager(workspace)
    asset = manager.get(asset_id)
    manager.update_status(asset_id, stage="building", status="running")

    style = load_style(style_id)
    shots_cfg = style.get("shots", {})

    if asset.paths.shots_json.exists():
        shots = read_json(asset.paths.shots_json)
    else:
        shots = detect_shots(asset.paths.source_video)
        write_json(asset.paths.shots_json, shots)
    min_shot_seconds = float(shots_cfg.get("min_duration", 10.0))
    highlight = select(shots, max_duration=60.0, min_shot_seconds=min_shot_seconds)
    write_json(asset.paths.highlight_json, highlight)

    crop = detect_letterbox_crop(asset.paths.source_video)
    write_json(asset.paths.crop_json, crop.to_dict())

    frame = style.get("frame")
    resolution = tuple(style["video"]["resolution"])
    build_ass_from_srt(
        asset.paths.subtitles_original,
        asset.paths.subtitles_ass,
        style,
        title=title,
        tagline=tagline,
        frame=frame,
        total_duration=sum(shot["end"] - shot["start"] for shot in highlight),
        source_video=asset.paths.source_video,
        shots=highlight,
    )
    fps = float(style["video"].get("fps", 30))
    transition_frames = shots_cfg.get("transition_frames")
    if transition_frames is not None:
        transition_duration = float(transition_frames) / max(fps, 1.0)
    else:
        transition_duration = float(shots_cfg.get("transition_duration", 0.15))

    render_reel(
        asset.paths.source_video,
        highlight,
        asset.paths.output_reel,
        ass_path=asset.paths.subtitles_ass,
        resolution=resolution,
        frame=frame,
        crop=crop.to_dict(),
        watermark_text=watermark,
        transition_duration=transition_duration,
        punch_zoom=shots_cfg.get("punch_zoom"),
    )

    manager.update_status(asset_id, stage="done", status="done")
    return asset.paths.output_reel


app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    asset_id: str,
    workspace: Optional[Path] = typer.Option(None, "--workspace"),
    style: str = typer.Option("reels_default", "--style"),
    title: Optional[str] = typer.Option(None, "--title"),
    tagline: Optional[str] = typer.Option(None, "--tagline"),
    watermark: Optional[str] = typer.Option(None, "--watermark"),
) -> None:
    """Build a 60s highlight reel from an asset."""
    output = build(
        asset_id,
        workspace,
        style_id=style,
        title=title,
        tagline=tagline,
        watermark=watermark,
    )
    typer.echo(str(output))
