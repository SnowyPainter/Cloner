from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from reels.assets import AssetManager
from reels.cli.output import IngestOutput, emit
from reels.download import SubtitleError, download_youtube, require_subtitles
from reels.utils.fs import read_json, write_json
from reels.video.shot_detect import detect_shots


def ingest(
    youtube_url: str,
    workspace: Optional[Path] = None,
    translate_lang: Optional[str] = None,
) -> str:
    manager = AssetManager(workspace)
    asset = manager.create(youtube_url)
    manager.update_status(asset.asset_id, stage="downloading", status="running")

    download_youtube(youtube_url, asset.paths.source_video, asset.paths.subtitles_dir)
    try:
        require_subtitles(asset.paths.subtitles_original)
    except SubtitleError:
        from reels.audio.transcribe import transcribe_to_srt

        transcribe_to_srt(asset.paths.source_video, asset.paths.subtitles_original, model="small")

    if translate_lang:
        from reels.subtitles.translate import target_srt_path, translate_srt

        translated_path = target_srt_path(asset.paths.subtitles_dir, translate_lang)
        translate_srt(
            asset.paths.subtitles_original,
            translated_path,
            target_lang=translate_lang,
            audio_path=asset.paths.source_video,
        )

    shots = detect_shots(asset.paths.source_video)
    write_json(asset.paths.shots_json, shots)

    _update_asset_metadata(manager, asset)
    manager.update_status(asset.asset_id, stage="downloaded", status="done")
    return asset.asset_id


def _update_asset_metadata(manager: AssetManager, asset) -> None:
    info_path = asset.paths.source_video.with_suffix(".info.json")
    if not info_path.exists():
        return

    info = read_json(info_path)
    title = str(info.get("title", ""))
    duration = float(info.get("duration", 0.0))

    asset.title = title
    asset.duration = duration
    manager.update_asset(asset)


app = typer.Typer(no_args_is_help=True)


@app.command()
def run(
    youtube_url: str,
    workspace: Optional[Path] = typer.Option(None, "--workspace"),
    translate: Optional[str] = typer.Option(
        None,
        "--translate",
        help="Translate subtitles to target language (MarianMT).",
    ),
) -> None:
    """Ingest a YouTube URL into an asset folder."""
    asset_id = ingest(youtube_url, workspace, translate_lang=translate)
    payload: IngestOutput = {
        "schema": "reels.cli.ingest.v1",
        "asset_id": asset_id,
    }
    emit(payload)
