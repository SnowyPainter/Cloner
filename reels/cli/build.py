from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reels.assets import AssetManager
from reels.cli.output import BuildOutput, emit
from reels.subtitles import build_ass_from_srt, load_style
from reels.subtitles.translate import target_srt_path
from reels.utils.fs import read_json, write_json
from reels.video.highlight import select_bundles
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
    translated_lang: Optional[str] = None,
    count: int = 1,
) -> list[Path]:
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
    bundles = select_bundles(
        shots,
        max_duration=60.0,
        min_shot_seconds=min_shot_seconds,
        max_count=count,
    )
    if not bundles:
        raise ValueError("No highlight shots available for rendering")
    if bundles:
        write_json(asset.paths.highlight_json, bundles[0])

    crop = detect_letterbox_crop(asset.paths.source_video)
    write_json(asset.paths.crop_json, crop.to_dict())

    frame = style.get("frame")
    resolution = tuple(style["video"]["resolution"])
    translated_path = None
    if translated_lang:
        candidate = target_srt_path(asset.paths.subtitles_dir, translated_lang)
        if candidate.exists():
            translated_path = candidate

    output_paths: list[Path] = []
    fps = float(style["video"].get("fps", 30))
    transition_frames = shots_cfg.get("transition_frames")
    if transition_frames is not None:
        transition_duration = float(transition_frames) / max(fps, 1.0)
    else:
        transition_duration = float(shots_cfg.get("transition_duration", 0.15))

    base_output = asset.paths.output_reel
    base_ass = asset.paths.subtitles_ass
    base_highlight = asset.paths.highlight_json
    for idx, highlight in enumerate(bundles, start=1):
        output_path = base_output
        ass_path = base_ass
        highlight_path = base_highlight
        if idx > 1:
            output_path = base_output.with_name(f"{base_output.stem}_{idx}{base_output.suffix}")
            ass_path = base_ass.with_name(f"{base_ass.stem}_{idx}{base_ass.suffix}")
            highlight_path = base_highlight.with_name(f"{base_highlight.stem}_{idx}{base_highlight.suffix}")
            write_json(highlight_path, highlight)

        build_ass_from_srt(
            asset.paths.subtitles_original,
            ass_path,
            style,
            title=title,
            tagline=tagline,
            frame=frame,
            total_duration=sum(shot["end"] - shot["start"] for shot in highlight),
            source_video=asset.paths.source_video,
            shots=highlight,
            secondary_srt_path=translated_path,
        )

        render_reel(
            asset.paths.source_video,
            highlight,
            output_path,
            ass_path=ass_path,
            resolution=resolution,
            frame=frame,
            crop=crop.to_dict(),
            watermark_text=watermark,
            transition_duration=transition_duration,
            punch_zoom=shots_cfg.get("punch_zoom"),
        )
        output_paths.append(output_path)

    manager.update_status(asset_id, stage="done", status="done")
    return output_paths


app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    asset_id: str,
    workspace: Optional[Path] = typer.Option(None, "--workspace"),
    style: str = typer.Option("reels_default", "--style"),
    title: Optional[str] = typer.Option(None, "--title"),
    tagline: Optional[str] = typer.Option(None, "--tagline"),
    watermark: Optional[str] = typer.Option(None, "--watermark"),
    count: int = typer.Option(1, "--count", min=1, help="Maximum number of reels to build."),
    translated_lang: Optional[str] = typer.Option(
        None,
        "--translated-lang",
        help="Render draft-translated subtitles below the original (e.g. ko).",
    ),
) -> None:
    """Build a 60s highlight reel from an asset."""
    output = build(
        asset_id,
        workspace,
        style_id=style,
        title=title,
        tagline=tagline,
        watermark=watermark,
        translated_lang=translated_lang,
        count=count,
    )
    payload: BuildOutput = {
        "schema": "reels.cli.build.v1",
        "asset_id": asset_id,
        "output_path": str(output[0]) if output else "",
        "output_paths": [str(path) for path in output],
    }
    emit(payload)
