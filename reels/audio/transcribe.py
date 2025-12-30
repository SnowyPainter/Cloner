from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable


def transcribe_to_srt(video_path: Path, srt_path: Path, model: str = "small") -> Path:
    if srt_path.exists():
        return srt_path

    try:
        import whisper
    except Exception as exc:
        raise RuntimeError("openai-whisper package is required to transcribe subtitles") from exc

    logging.info("Transcribing subtitles with whisper model=%s", model)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    result = whisper.load_model(model).transcribe(str(video_path))
    _write_srt(srt_path, result.get("segments", []))
    return srt_path


def _write_srt(path: Path, segments: Iterable[dict]) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = _format_timestamp(float(segment.get("start", 0.0)))
        end = _format_timestamp(float(segment.get("end", 0.0)))
        text = str(segment.get("text", "")).strip()
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000.0))
    hours, rem = divmod(millis, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
