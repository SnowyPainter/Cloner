from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np

from reels.video.reader import _open_container


@dataclass(frozen=True)
class CropInfo:
    x: int
    y: int
    size: int
    content_top: int
    content_bottom: int
    content_width: int
    content_height: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "content_top": self.content_top,
            "content_bottom": self.content_bottom,
            "content_width": self.content_width,
            "content_height": self.content_height,
        }


def detect_letterbox_crop(
    video_path: Path,
    sample_frames: int = 10,
    threshold: float = 10.0,
) -> CropInfo:
    with _open_container(video_path) as container:
        stream = container.streams.video[0]
        width = int(stream.width)
        height = int(stream.height)

        tops: List[int] = []
        bottoms: List[int] = []
        count = 0

        for frame in container.decode(video=0):
            gray = frame.to_ndarray(format="gray")
            top = _detect_top(gray, threshold)
            bottom = _detect_bottom(gray, threshold)
            tops.append(top)
            bottoms.append(bottom)
            count += 1
            if count >= sample_frames:
                break

    if not tops or not bottoms:
        raise ValueError("Unable to sample frames for letterbox detection")

    top = int(np.median(tops))
    bottom = int(np.median(bottoms))
    if bottom <= top:
        top = 0
        bottom = height

    content_height = bottom - top
    content_width = width
    size = min(content_width, content_height)
    x_center = content_width // 2
    x = max(x_center - size // 2, 0)

    return CropInfo(
        x=x,
        y=top,
        size=size,
        content_top=top,
        content_bottom=bottom,
        content_width=content_width,
        content_height=content_height,
    )


def _detect_top(gray: np.ndarray, threshold: float) -> int:
    height = gray.shape[0]
    for y in range(height):
        if gray[y].mean() > threshold:
            return y
    return 0


def _detect_bottom(gray: np.ndarray, threshold: float) -> int:
    height = gray.shape[0]
    for y in range(height - 1, -1, -1):
        if gray[y].mean() > threshold:
            return y
    return height
