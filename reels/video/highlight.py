from __future__ import annotations

from typing import Dict, Iterable, List


def select(
    shots: Iterable[Dict[str, float]],
    max_duration: float = 60.0,
    min_shot_seconds: float = 10.0,
) -> List[Dict[str, float]]:
    shot_list = _filter_short_shots(list(shots), min_shot_seconds)
    if not shot_list:
        return []

    if any("score" in shot for shot in shot_list):
        selected = _select_by_score(shot_list, max_duration)
        return sorted(selected, key=lambda s: float(s["start"]))

    return _select_by_duration(shot_list, max_duration)


def _select_by_duration(
    shots: Iterable[Dict[str, float]],
    max_duration: float,
) -> List[Dict[str, float]]:
    result: List[Dict[str, float]] = []
    total = 0.0

    for shot in shots:
        start = float(shot["start"])
        end = float(shot["end"])
        duration = end - start
        if duration <= 0:
            continue

        remaining = max_duration - total
        if remaining <= 0:
            break

        if duration <= remaining:
            result.append({"start": start, "end": end})
            total += duration
            continue

        result.append({"start": start, "end": start + remaining})
        total += remaining
        break

    return result


def _select_by_score(
    shots: List[Dict[str, float]],
    max_duration: float,
) -> List[Dict[str, float]]:
    ranked = sorted(shots, key=lambda s: float(s.get("score", 0.0)), reverse=True)
    result: List[Dict[str, float]] = []
    total = 0.0

    for shot in ranked:
        start = float(shot["start"])
        end = float(shot["end"])
        duration = end - start
        if duration <= 0:
            continue
        if total + duration > max_duration:
            continue
        result.append(shot)
        total += duration
        if total >= max_duration:
            break

    return result


def _filter_short_shots(
    shots: List[Dict[str, float]],
    min_shot_seconds: float,
) -> List[Dict[str, float]]:
    if min_shot_seconds <= 0:
        return shots
    result: List[Dict[str, float]] = []
    for shot in shots:
        start = float(shot["start"])
        end = float(shot["end"])
        if end - start >= min_shot_seconds:
            result.append(shot)
    return result