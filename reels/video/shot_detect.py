from __future__ import annotations

from pathlib import Path
from typing import List, Dict

from reels.video.reader import get_duration_seconds


def detect_shots(video_path: Path) -> List[Dict[str, float]]:
    """Return a minimal shot list covering the full video.

    This keeps the MVP deterministic and makes the pipeline functional
    before adding more complex scene detection.
    """
    duration = get_duration_seconds(video_path)
    if duration <= 0:
        raise ValueError("Unable to determine video duration")
    return [{"start": 0.0, "end": duration}]
