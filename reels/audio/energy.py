from __future__ import annotations

from pathlib import Path
from typing import Tuple

import av
import numpy as np


def extract_audio_energy(video_path: Path) -> Tuple[np.ndarray, np.ndarray]:
    container = av.open(str(video_path))
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if audio_stream is None:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    times = []
    energies = []
    for frame in container.decode(audio_stream):
        samples = frame.to_ndarray().astype(np.float32)
        if samples.size == 0:
            continue
        rms = float(np.sqrt(np.mean(samples**2)))
        if frame.time is not None:
            timestamp = float(frame.time)
        elif frame.pts is not None and frame.time_base is not None:
            timestamp = float(frame.pts * frame.time_base)
        else:
            timestamp = 0.0
        times.append(timestamp)
        energies.append(rms)

    return np.array(times, dtype=np.float32), np.array(energies, dtype=np.float32)


def energy_bounds(
    energies: np.ndarray,
    low_percentile: float = 5.0,
    high_percentile: float = 95.0,
) -> Tuple[float, float]:
    if energies.size == 0:
        return 0.0, 1.0
    low = float(np.percentile(energies, low_percentile))
    high = float(np.percentile(energies, high_percentile))
    if high <= low:
        high = low + 1e-6
    return low, high
