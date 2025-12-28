from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Iterable, List

from reels.video.reader import has_audio


class RenderError(RuntimeError):
    pass


def render_reel(
    source_video: Path,
    shots: Iterable[Dict[str, float]],
    output_path: Path,
    ass_path: Path | None = None,
    resolution: tuple[int, int] | None = None,
    frame: Dict[str, object] | None = None,
    crop: Dict[str, int] | None = None,
    watermark_text: str | None = None,
    watermark_opacity: float = 0.25,
) -> None:
    shot_list: List[Dict[str, float]] = list(shots)
    if not shot_list:
        raise RenderError("No shots provided for rendering")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    include_audio = has_audio(source_video)
    trim_parts: List[str] = []
    frame_parts: List[str] = []
    vlabels: List[str] = []
    alabels: List[str] = []

    for idx, shot in enumerate(shot_list):
        start = float(shot["start"])
        end = float(shot["end"])
        vlabel = f"v{idx}"
        trim_parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[{vlabel}]"
        )
        vlabels.append(f"[{vlabel}]")

        if include_audio:
            alabel = f"a{idx}"
            trim_parts.append(
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[{alabel}]"
            )
            alabels.append(f"[{alabel}]")

    if include_audio:
        concat_inputs: List[str] = []
        for vlabel, alabel in zip(vlabels, alabels):
            concat_inputs.append(vlabel)
            concat_inputs.append(alabel)
        concat = "".join(concat_inputs) + f"concat=n={len(shot_list)}:v=1:a=1[vcat][acat]"
    else:
        concat = "".join(vlabels) + f"concat=n={len(shot_list)}:v=1:a=0[vcat]"

    vbase = "[vcat]"
    if frame and frame.get("mode") == "square_center":
        if not resolution:
            raise RenderError("resolution is required for square_center framing")
        width, height = resolution
        size = min(width, height)
        blur = int(frame.get("blur", 30))
        frame_parts.append(f"{vbase}split=2[bgsrc][fgsrc]")
        if crop:
            content_top = crop["content_top"]
            content_height = crop["content_height"]
            content_width = crop["content_width"]
            crop_x = crop["x"]
            crop_y = crop["y"]
            crop_size = crop["size"]
            bg_crop = f"crop={content_width}:{content_height}:0:{content_top}"
            fg_crop = f"crop={crop_size}:{crop_size}:{crop_x}:{crop_y}"
        else:
            bg_crop = None
            fg_crop = None
        bg_chain = "[bgsrc]"
        if bg_crop:
            bg_chain += f"{bg_crop},"
        bg_chain += (
            f"scale=w={width}:h={height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},boxblur={blur}:1[bg]"
        )
        frame_parts.append(bg_chain)

        fg_chain = "[fgsrc]"
        if fg_crop:
            fg_chain += f"{fg_crop},"
        fg_chain += f"scale=w={size}:h={size}:force_original_aspect_ratio=increase,crop={size}:{size}[fg]"
        frame_parts.append(fg_chain)
        frame_parts.append("[bg][fg]overlay=(W-w)/2:(H-h)/2[vframe]")
        vbase = "[vframe]"

    filters: List[str] = []
    if resolution and (not frame or frame.get("mode") != "square_center"):
        width, height = resolution
        filters.append(f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease")
        filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black")
    if watermark_text:
        opacity = max(0.0, min(float(watermark_opacity), 1.0))
        if resolution:
            _, height = resolution
            font_size = max(int(height * 0.06), 24)
        else:
            font_size = 48
        safe_text = _ffmpeg_escape_text(watermark_text)
        filters.append(
            "drawtext=text='{text}':x=(w-text_w)/2:y=(h-text_h)/2:"
            "fontsize={size}:fontcolor=white@{alpha}".format(
                text=safe_text,
                size=font_size,
                alpha=opacity,
            )
        )
    if ass_path:
        filters.append(f"subtitles='{_ffmpeg_escape_path(ass_path)}'")

    filter_chain = vbase
    if filters:
        filter_chain += filters[0]
        if len(filters) > 1:
            filter_chain += "," + ",".join(filters[1:])
    filter_chain += "[outv]"

    filter_complex = ";".join(trim_parts + [concat] + frame_parts + [filter_chain])

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_video),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
    ]
    if include_audio:
        cmd += ["-map", "[acat]"]
    cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        details = result.stderr.strip() or "ffmpeg render failed"
        raise RenderError(f"{details}\nfilter_complex={filter_complex}")


def _ffmpeg_escape_path(path: Path) -> str:
    value = str(path).replace("\\", "/")
    return value.replace(":", "\\:")


def _ffmpeg_escape_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )
