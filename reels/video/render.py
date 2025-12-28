from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Iterable, List

from reels.video.reader import has_audio


class RenderError(RuntimeError):
    pass


def render_reel(source_video: Path, shots: Iterable[Dict[str, float]], output_path: Path) -> None:
    shot_list: List[Dict[str, float]] = list(shots)
    if not shot_list:
        raise RenderError("No shots provided for rendering")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    include_audio = has_audio(source_video)
    filter_parts: List[str] = []
    vlabels: List[str] = []
    alabels: List[str] = []

    for idx, shot in enumerate(shot_list):
        start = float(shot["start"])
        end = float(shot["end"])
        vlabel = f"v{idx}"
        filter_parts.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[{vlabel}]"
        )
        vlabels.append(f"[{vlabel}]")

        if include_audio:
            alabel = f"a{idx}"
            filter_parts.append(
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[{alabel}]"
            )
            alabels.append(f"[{alabel}]")

    if include_audio:
        concat = "".join(vlabels + alabels) + f"concat=n={len(shot_list)}:v=1:a=1[outv][outa]"
    else:
        concat = "".join(vlabels) + f"concat=n={len(shot_list)}:v=1:a=0[outv]"

    filter_complex = ";".join(filter_parts + [concat])

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
        cmd += ["-map", "[outa]"]
    cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(result.stderr.strip() or "ffmpeg render failed")
