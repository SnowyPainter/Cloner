from __future__ import annotations

from typing import Dict, Iterable, List


def select(
    shots: Iterable[Dict[str, float]],
    max_duration: float = 60.0,
) -> List[Dict[str, float]]:
    shot_list = list(shots)
    if not shot_list:
        return []

    if any("score" in shot for shot in shot_list):
        selected = _select_max_score(shot_list, max_duration)
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


def _select_max_score(
    shots: List[Dict[str, float]],
    max_duration: float,
    step_seconds: float = 0.1,
) -> List[Dict[str, float]]:
    durations: List[int] = []
    scores: List[float] = []
    for shot in shots:
        start = float(shot["start"])
        end = float(shot["end"])
        duration = max(end - start, 0.0)
        steps = max(int(round(duration / step_seconds)), 1)
        durations.append(steps)
        scores.append(float(shot.get("score", 0.0)))

    max_steps = max(int(round(max_duration / step_seconds)), 1)
    n = len(shots)

    dp = [-1.0] * (max_steps + 1)
    choose = [[False] * (max_steps + 1) for _ in range(n)]
    dp[0] = 0.0

    for i in range(n):
        dur = durations[i]
        score = scores[i]
        for t in range(max_steps, dur - 1, -1):
            if dp[t - dur] < 0:
                continue
            candidate = dp[t - dur] + score
            if candidate > dp[t]:
                dp[t] = candidate
                choose[i][t] = True

    best_time = max(range(max_steps + 1), key=lambda t: dp[t])
    selected: List[Dict[str, float]] = []
    t = best_time
    for i in range(n - 1, -1, -1):
        if choose[i][t]:
            selected.append(shots[i])
            t -= durations[i]
    return list(reversed(selected))
