from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import av

from reels.audio.energy import energy_bounds, extract_audio_energy
from reels.video.reader import get_duration_seconds


def detect_shots(
    video_path: Path,
    sample_fps: float = 3.0,
    min_shot_seconds: float = 0.8,
    diff_min: float = 0.08,
    diff_percentile: float = 90.0,
    diff_multiplier: float = 1.1,
    motion_weight: float = 0.6,
    audio_weight: float = 0.4,
) -> List[Dict[str, float]]:
    duration = get_duration_seconds(video_path)
    if duration <= 0:
        raise ValueError("Unable to determine video duration")

    times, diffs = _sample_frame_diffs(video_path, sample_fps)
    if not diffs:
        return [{"start": 0.0, "end": duration, "score": 0.0}]

    threshold = max(diff_min, float(np.percentile(diffs, diff_percentile)) * diff_multiplier)
    cut_times = [t for t, diff in zip(times, diffs) if diff >= threshold]
    shots = _build_shots(duration, cut_times, min_shot_seconds)

    shot_motion = _shot_motion_scores(shots, times, diffs)
    shot_audio = _shot_audio_scores(shots, video_path)
    motion_norm = _normalize_scores(shot_motion)
    audio_norm = _normalize_scores(shot_audio)

    for idx, shot in enumerate(shots):
        score = motion_weight * motion_norm[idx] + audio_weight * audio_norm[idx]
        shot["motion"] = float(shot_motion[idx])
        shot["audio"] = float(shot_audio[idx])
        shot["score"] = float(score)
    return shots


def _sample_frame_diffs(video_path: Path, sample_fps: float) -> Tuple[List[float], List[float]]:
    container = av.open(str(video_path))
    if not container.streams.video:
        return [], []
    stream = container.streams.video[0]
    interval = 1.0 / max(sample_fps, 0.1)

    last_time: float | None = None
    prev_frame: np.ndarray | None = None
    times: List[float] = []
    diffs: List[float] = []

    for frame in container.decode(stream):
        if frame.time is None:
            continue
        if last_time is not None and frame.time - last_time < interval:
            continue
        last_time = float(frame.time)
        gray = frame.to_ndarray(format="gray").astype(np.float32) / 255.0
        gray = gray[::8, ::8]
        if prev_frame is not None:
            diff = float(np.mean(np.abs(gray - prev_frame)))
            times.append(float(frame.time))
            diffs.append(diff)
        prev_frame = gray

    return times, diffs


def _build_shots(duration: float, cut_times: List[float], min_shot_seconds: float) -> List[Dict[str, float]]:
    cuts = [0.0] + sorted(t for t in cut_times if 0.0 < t < duration) + [duration]
    shots: List[Dict[str, float]] = []
    start = cuts[0]
    for end in cuts[1:]:
        if end - start < min_shot_seconds and shots:
            shots[-1]["end"] = end
        else:
            shots.append({"start": start, "end": end})
        start = end
    return [shot for shot in shots if shot["end"] - shot["start"] > 0]


def _shot_motion_scores(
    shots: List[Dict[str, float]],
    times: List[float],
    diffs: List[float],
) -> List[float]:
    scores: List[float] = []
    time_array = np.array(times, dtype=np.float32)
    diff_array = np.array(diffs, dtype=np.float32)
    for shot in shots:
        start = float(shot["start"])
        end = float(shot["end"])
        mask = (time_array >= start) & (time_array <= end)
        if np.any(mask):
            scores.append(float(np.mean(diff_array[mask])))
        else:
            scores.append(0.0)
    return scores


def _shot_audio_scores(shots: List[Dict[str, float]], video_path: Path) -> List[float]:
    times, energies = extract_audio_energy(video_path)
    if energies.size == 0:
        return [0.0 for _ in shots]
    scores: List[float] = []
    for shot in shots:
        scores.append(_average_energy(times, energies, shot["start"], shot["end"]))
    return scores


def _average_energy(
    times: np.ndarray,
    energies: np.ndarray,
    start_time: float,
    end_time: float,
) -> float:
    mask = (times >= start_time) & (times <= end_time)
    if np.any(mask):
        return float(np.mean(energies[mask]))
    mid = (start_time + end_time) / 2.0
    idx = int(np.searchsorted(times, mid))
    if idx <= 0:
        return float(energies[0])
    if idx >= len(times):
        return float(energies[-1])
    before = idx - 1
    if abs(times[idx] - mid) < abs(times[before] - mid):
        return float(energies[idx])
    return float(energies[before])


def _normalize_scores(values: List[float]) -> List[float]:
    if not values:
        return []
    array = np.array(values, dtype=np.float32)
    low, high = energy_bounds(array, 5.0, 95.0)
    if high <= low:
        return [0.0 for _ in values]
    normalized = (array - low) / (high - low)
    normalized = np.clip(normalized, 0.0, 1.0)
    return [float(value) for value in normalized]
