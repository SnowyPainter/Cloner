from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reels.assets import AssetManager
from reels.subtitles import build_ass_from_srt, load_style
from reels.utils.fs import write_json
from reels.video.highlight import select
from reels.video.letterbox import detect_letterbox_crop
from reels.video.render import render_reel
from reels.video.shot_detect import detect_shots


def build(
    asset_id: str,
    workspace: Optional[Path] = None,
    style_id: str = "reels_bold",
    title: Optional[str] = None,
    tagline: Optional[str] = None,
) -> Path:
    manager = AssetManager(workspace)
    asset = manager.get(asset_id)
    manager.update_status(asset_id, stage="building", status="running")

    shots = detect_shots(asset.paths.source_video)
    write_json(asset.paths.shots_json, shots)

    highlight = select(shots, max_duration=60.0)
    write_json(asset.paths.highlight_json, highlight)

    crop = detect_letterbox_crop(asset.paths.source_video)
    write_json(asset.paths.crop_json, crop.to_dict())

    style = load_style(style_id)
    build_ass_from_srt(
        asset.paths.subtitles_original,
        asset.paths.subtitles_ass,
        style,
        title=title,
        tagline=tagline,
    )
    resolution = tuple(style["video"]["resolution"])
    frame = style.get("frame")
    render_reel(
        asset.paths.source_video,
        highlight,
        asset.paths.output_reel,
        ass_path=asset.paths.subtitles_ass,
        resolution=resolution,
        frame=frame,
        crop=crop.to_dict(),
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
) -> None:
    """Build a 60s highlight reel from an asset."""
    output = build(asset_id, workspace, style_id=style, title=title, tagline=tagline)
    typer.echo(str(output))
