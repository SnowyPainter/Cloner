from __future__ import annotations

from typing import Dict, Iterable, List


def select(shots: Iterable[Dict[str, float]], max_duration: float = 60.0) -> List[Dict[str, float]]:
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

        # Trim the last shot to fit the remaining duration.
        result.append({"start": start, "end": start + remaining})
        total += remaining
        break

    return result
