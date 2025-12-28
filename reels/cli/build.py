from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reels.assets import AssetManager
from reels.utils.fs import write_json
from reels.video.highlight import select
from reels.video.render import render_reel
from reels.video.shot_detect import detect_shots


def build(asset_id: str, workspace: Optional[Path] = None) -> Path:
    manager = AssetManager(workspace)
    asset = manager.get(asset_id)
    manager.update_status(asset_id, stage="building", status="running")

    shots = detect_shots(asset.paths.source_video)
    write_json(asset.paths.shots_json, shots)

    highlight = select(shots, max_duration=60.0)
    write_json(asset.paths.highlight_json, highlight)

    render_reel(asset.paths.source_video, highlight, asset.paths.output_reel)

    manager.update_status(asset_id, stage="done", status="done")
    return asset.paths.output_reel


app = typer.Typer(no_args_is_help=True)


@app.command()
def run(asset_id: str, workspace: Optional[Path] = typer.Option(None, "--workspace")) -> None:
    """Build a 60s highlight reel from an asset."""
    output = build(asset_id, workspace)
    typer.echo(str(output))
