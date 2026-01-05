from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple


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


def select_bundles(
    shots: Iterable[Dict[str, float]],
    max_duration: float = 60.0,
    min_shot_seconds: float = 10.0,
    max_count: int = 1,
) -> List[List[Dict[str, float]]]:
    remaining = list(shots)
    bundles: List[List[Dict[str, float]]] = []
    count = max(int(max_count), 1)

    for _ in range(count):
        bundle = select(remaining, max_duration=max_duration, min_shot_seconds=min_shot_seconds)
        if not bundle:
            break
        bundles.append(bundle)
        ranges = [(float(shot["start"]), float(shot["end"])) for shot in bundle]
        remaining = _filter_short_shots(
            _remove_ranges(remaining, ranges),
            min_shot_seconds,
        )

    return bundles


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


def _remove_ranges(
    shots: List[Dict[str, float]],
    ranges: Sequence[Tuple[float, float]],
) -> List[Dict[str, float]]:
    if not ranges:
        return shots
    ordered = [(float(start), float(end)) for start, end in ranges if end > start]
    if not ordered:
        return shots
    ordered.sort(key=lambda item: item[0])

    result: List[Dict[str, float]] = []
    for shot in shots:
        start = float(shot["start"])
        end = float(shot["end"])
        if end <= start:
            continue
        segments = [(start, end)]
        for cut_start, cut_end in ordered:
            next_segments: List[Tuple[float, float]] = []
            for seg_start, seg_end in segments:
                if cut_end <= seg_start or cut_start >= seg_end:
                    next_segments.append((seg_start, seg_end))
                    continue
                if cut_start > seg_start:
                    next_segments.append((seg_start, min(cut_start, seg_end)))
                if cut_end < seg_end:
                    next_segments.append((max(cut_end, seg_start), seg_end))
            segments = next_segments
            if not segments:
                break
        for seg_start, seg_end in segments:
            if seg_end <= seg_start:
                continue
            clipped = dict(shot)
            clipped["start"] = seg_start
            clipped["end"] = seg_end
            result.append(clipped)
    return result
