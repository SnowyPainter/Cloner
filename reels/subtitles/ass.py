from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import re
import string

import numpy as np

import pysubs2

from reels.audio.energy import energy_bounds, extract_audio_energy
from reels.utils.fs import read_json


class StyleError(RuntimeError):
    pass


def load_style(style_id: str) -> Dict[str, object]:
    style_dir = Path(__file__).resolve().parents[1] / "styles"
    name = style_id
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = style_dir / name
    if not path.exists():
        raise StyleError(f"Style not found: {style_id}")
    return read_json(path)


def build_ass_from_srt(
    srt_path: Path,
    ass_path: Path,
    style: Dict[str, object],
    title: Optional[str] = None,
    tagline: Optional[str] = None,
    frame: Optional[Dict[str, object]] = None,
    total_duration: Optional[float] = None,
    source_video: Optional[Path] = None,
    shots: Optional[List[Dict[str, float]]] = None,
) -> None:
    subs = pysubs2.load(str(srt_path))
    video = style["video"]
    res_x, res_y = video["resolution"]
    layout = style["subtitles"]["layout"]
    base = style["subtitles"]["base_style"]
    highlight = style["subtitles"]["highlight"]
    overlays = style.get("overlays", {})
    title_cfg, tagline_cfg = _resolve_overlay_positions(
        overlays, res_x, res_y, frame
    )

    energy_data: Optional[Tuple[np.ndarray, np.ndarray, float, float]] = None
    if source_video and _use_energy_palette(highlight):
        times, energies = extract_audio_energy(source_video)
        if energies.size:
            low_pct = float(highlight.get("energy_percentile_min", 5.0))
            high_pct = float(highlight.get("energy_percentile_max", 95.0))
            e_min, e_max = energy_bounds(energies, low_pct, high_pct)
            energy_data = (times, energies, e_min, e_max)

    header = _build_header(res_x, res_y, layout, base, highlight, title_cfg, tagline_cfg)
    subtitle_lines: Iterable[SubtitleLineLike] = subs
    if shots:
        subtitle_lines = _clip_subs_to_shots(subs, shots)
    events = _build_events(subtitle_lines, layout, highlight, energy_data)
    if title or tagline:
        events = _prepend_overlays(events, title, tagline, total_duration, subs)

    ass_path.write_text(header + "\n" + "\n".join(events) + "\n", encoding="utf-8")


def _build_header(
    res_x: int,
    res_y: int,
    layout: Dict[str, object],
    base: Dict[str, object],
    highlight: Dict[str, object],
    title_cfg: Optional[Dict[str, object]],
    tagline_cfg: Optional[Dict[str, object]],
) -> str:
    primary = highlight.get("inactive_color", base["color"])
    secondary = highlight.get("active_color", base["color"])
    outline = base.get("outline_color", "&H00000000")
    shadow = base.get("shadow_color", "&H64000000")

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {res_x}",
        f"PlayResY: {res_y}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,{font},{size},{primary},{secondary},{outline},{shadow},{bold},{italic},0,0,100,100,0,0,1,{outline_w},{shadow_w},{align},{margin_h},{margin_h},{margin_v},1".format(
            font=base["font"],
            size=base["size"],
            primary=primary,
            secondary=secondary,
            outline=outline,
            shadow=shadow,
            bold=-1 if base.get("bold", True) else 0,
            italic=-1 if base.get("italic", False) else 0,
            outline_w=base.get("outline", 3),
            shadow_w=base.get("shadow", 2),
            align=layout.get("alignment", 5),
            margin_h=layout.get("margin_h", 0),
            margin_v=layout.get("margin_v", 0),
        ),
    ]

    if title_cfg:
        lines.append(
            "Style: Title,{font},{size},{primary},{secondary},{outline},{shadow},{bold},{italic},0,0,100,100,0,0,1,{outline_w},{shadow_w},{align},{margin_h},{margin_h},{margin_v},1".format(
                font=title_cfg.get("font", base["font"]),
                size=title_cfg.get("size", base["size"]),
                primary=title_cfg.get("color", primary),
                secondary=secondary,
                outline=title_cfg.get("outline_color", outline),
                shadow=title_cfg.get("shadow_color", shadow),
                bold=-1 if title_cfg.get("bold", True) else 0,
                italic=-1 if title_cfg.get("italic", False) else 0,
                outline_w=title_cfg.get("outline", base.get("outline", 3)),
                shadow_w=title_cfg.get("shadow", base.get("shadow", 2)),
                align=title_cfg.get("alignment", 2),
                margin_h=title_cfg.get("margin_h", 0),
                margin_v=title_cfg.get("margin_v", 60),
            )
        )
    if tagline_cfg:
        lines.append(
            "Style: Tagline,{font},{size},{primary},{secondary},{outline},{shadow},{bold},{italic},0,0,100,100,0,0,1,{outline_w},{shadow_w},{align},{margin_h},{margin_h},{margin_v},1".format(
                font=tagline_cfg.get("font", base["font"]),
                size=tagline_cfg.get("size", base["size"]),
                primary=tagline_cfg.get("color", primary),
                secondary=secondary,
                outline=tagline_cfg.get("outline_color", outline),
                shadow=tagline_cfg.get("shadow_color", shadow),
                bold=-1 if tagline_cfg.get("bold", True) else 0,
                italic=-1 if tagline_cfg.get("italic", False) else 0,
                outline_w=tagline_cfg.get("outline", base.get("outline", 3)),
                shadow_w=tagline_cfg.get("shadow", base.get("shadow", 2)),
                align=tagline_cfg.get("alignment", 8),
                margin_h=tagline_cfg.get("margin_h", 0),
                margin_v=tagline_cfg.get("margin_v", 80),
            )
        )

    lines += ["", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    return "\n".join(lines)


def _build_events(
    subs: Iterable["SubtitleLineLike"],
    layout: Dict[str, object],
    highlight: Dict[str, object],
    energy_data: Optional[Tuple[np.ndarray, np.ndarray, float, float]],
) -> List[str]:
    events_data: List[Tuple[int, int, str]] = []
    max_chars = int(layout.get("max_chars_per_line", 18))
    max_lines = int(layout.get("max_lines", 2))
    min_word = float(highlight.get("min_word_duration", 0.08))
    max_word = float(highlight.get("max_word_duration", 0.2))
    energy_palette = _normalize_palette(highlight.get("energy_palette", []))
    use_energy = bool(energy_palette and energy_data)

    for line in subs:
        start_ms = int(line.start)
        end_ms = int(line.end)
        text = line.text.replace("\\N", " ").replace("\n", " ")
        text = re.sub(r"\[[^\]]*]", "", text)
        text = re.sub(r"(>>|<<)", "", text)
        text = text.strip()
        words = [w for w in text.split() if w]
        if not words:
            continue

        if end_ms <= start_ms:
            end_ms = start_ms + 10
        duration = max((end_ms - start_ms) / 1000.0, 0.01)
        weights = _word_weights(words, highlight)
        durations = _allocate_karaoke_durations(duration, weights, min_word, max_word)
        word_colors: Optional[List[str]] = None
        if use_energy and energy_data:
            source_start_ms = _line_source_start_ms(line)
            word_colors = _energy_colors_for_words(
                words,
                durations,
                source_start_ms / 1000.0,
                energy_data,
                energy_palette,
                highlight,
            )

        text_with_k = _apply_karaoke(words, durations, word_colors, highlight)
        text_with_k = _wrap_karaoke(text_with_k, max_chars, max_lines)
        if events_data and start_ms < events_data[-1][1]:
            prev_start, prev_end, prev_text = events_data[-1]
            adjusted_end = max(start_ms, prev_start + 10)
            events_data[-1] = (prev_start, adjusted_end, prev_text)
        events_data.append((start_ms, end_ms, text_with_k))

    events: List[str] = []
    for start_ms, end_ms, text_with_k in events_data:
        start = _format_time(start_ms)
        end = _format_time(end_ms)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text_with_k}")
    return events


def _prepend_overlays(
    events: List[str],
    title: Optional[str],
    tagline: Optional[str],
    total_duration: Optional[float],
    subs: pysubs2.SSAFile,
) -> List[str]:
    results = list(events)
    duration_ms = _resolve_total_duration_ms(total_duration, subs)
    if title:
        start = "0:00:00.00"
        end = _format_time(duration_ms)
        results.insert(0, f"Dialogue: 1,{start},{end},Title,,0,0,0,,{title}")
    if tagline:
        start = "0:00:00.00"
        end = _format_time(duration_ms)
        results.insert(0, f"Dialogue: 1,{start},{end},Tagline,,0,0,0,,{tagline}")
    return results


def _apply_karaoke(
    words: List[str],
    durations: Iterable[float],
    colors: Optional[List[str]],
    highlight: Dict[str, object],
) -> str:
    parts = []
    color_tag = str(highlight.get("energy_color_tag", "\\2c"))
    for idx, (word, dur) in enumerate(zip(words, durations)):
        centis = max(int(round(dur * 100)), 1)
        color = colors[idx] if colors and idx < len(colors) else None
        if color:
            parts.append(f"{{\\k{centis}{color_tag}{color}&}}{word}")
        else:
            parts.append(f"{{\\k{centis}}}{word}")
    return " ".join(parts)


def _normalize_palette(raw_palette: object) -> List[str]:
    palette: List[str] = []
    if not isinstance(raw_palette, list):
        return palette
    for item in raw_palette:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value:
            continue
        if not value.startswith("&H"):
            value = f"&H{value.lstrip('&')}"
        palette.append(value)
    return palette


def _use_energy_palette(highlight: Dict[str, object]) -> bool:
    if str(highlight.get("color_mode", "")).lower() == "energy":
        return True
    return bool(highlight.get("energy_palette"))


def _energy_colors_for_words(
    words: List[str],
    durations: List[float],
    start_time: float,
    energy_data: Tuple[np.ndarray, np.ndarray, float, float],
    palette: List[str],
    highlight: Dict[str, object],
) -> List[str]:
    times, energies, e_min, e_max = energy_data
    levels = len(palette)
    if levels == 0:
        return []

    silence_threshold = float(highlight.get("energy_silence_threshold", 0.08))
    max_step = int(highlight.get("energy_level_max_step", 1))
    prev_level = 0
    colors: List[str] = []
    cursor = start_time

    for idx, dur in enumerate(durations):
        word_start = cursor
        word_end = cursor + dur
        cursor = word_end
        avg_energy = _average_energy(times, energies, word_start, word_end)
        norm = (avg_energy - e_min) / (e_max - e_min + 1e-6)
        norm = float(min(max(norm, 0.0), 1.0))
        if norm < silence_threshold:
            level = 0
        else:
            level = int(norm * (levels - 1))
        if idx > 0 and max_step > 0:
            level = min(prev_level + max_step, level)
            level = max(prev_level - max_step, level)
        level = max(0, min(level, levels - 1))
        colors.append(palette[level])
        prev_level = level

    return colors


def _average_energy(
    times: np.ndarray,
    energies: np.ndarray,
    start_time: float,
    end_time: float,
) -> float:
    if times.size == 0:
        return 0.0
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


@dataclass
class SubtitleLine:
    start: int
    end: int
    text: str
    source_start: int


SubtitleLineLike = SubtitleLine | pysubs2.SSAEvent


def _line_source_start_ms(line: SubtitleLineLike) -> int:
    if isinstance(line, SubtitleLine):
        return int(line.source_start)
    return int(line.start)


def _clip_subs_to_shots(
    subs: pysubs2.SSAFile,
    shots: List[Dict[str, float]],
) -> List[SubtitleLine]:
    lines = list(subs)
    result: List[SubtitleLine] = []
    offset_seconds = 0.0

    for shot in shots:
        shot_start = float(shot["start"])
        shot_end = float(shot["end"])
        if shot_end <= shot_start:
            continue
        for line in lines:
            line_start = line.start / 1000.0
            line_end = line.end / 1000.0
            if line_end <= shot_start or line_start >= shot_end:
                continue
            clip_start = max(line_start, shot_start)
            clip_end = min(line_end, shot_end)
            if clip_end <= clip_start:
                continue
            new_start = int((clip_start - shot_start + offset_seconds) * 1000)
            new_end = int((clip_end - shot_start + offset_seconds) * 1000)
            if new_end <= new_start:
                new_end = new_start + 10
            result.append(
                SubtitleLine(
                    start=new_start,
                    end=new_end,
                    text=line.text,
                    source_start=int(clip_start * 1000),
                )
            )
        offset_seconds += shot_end - shot_start

    return result


def _word_weights(words: List[str], highlight: Dict[str, object]) -> List[float]:
    raw_stopwords = highlight.get("stopwords", [])
    stopwords = {
        word.strip().lower()
        for word in raw_stopwords
        if isinstance(word, str) and word.strip()
    }
    meaning_weight = float(highlight.get("meaning_weight", 1.2))
    stopword_weight = float(highlight.get("stopword_weight", 0.6))
    length_weight = float(highlight.get("length_weight", 0.05))

    weights: List[float] = []
    for word in words:
        normalized = _normalize_word(word)
        length = max(len(normalized), 1)
        weight = 1.0 + length_weight * length
        if normalized and normalized in stopwords:
            weight *= stopword_weight
        else:
            weight *= meaning_weight
        weights.append(max(weight, 0.01))
    return weights


def _normalize_word(word: str) -> str:
    return word.strip(string.punctuation).lower()


def _allocate_karaoke_durations(
    duration: float,
    weights: List[float],
    min_word: float,
    max_word: float,
) -> List[float]:
    if not weights:
        return []

    count = len(weights)
    average = duration / count if count else duration
    effective_min = min(min_word, average) if min_word > 0 else 0.0
    effective_max = max_word if max_word > 0 else duration

    total_weight = sum(weights) or count
    durations: List[float] = []
    for weight in weights:
        raw = duration * weight / total_weight
        durations.append(min(max(raw, effective_min), effective_max))

    total = sum(durations)
    if durations:
        durations[-1] = max(durations[-1] + (duration - total), 0.01)
    return durations


def _wrap_karaoke(text: str, max_chars: int, max_lines: int) -> str:
    tokens = text.split()
    if not tokens:
        return text

    lines: List[str] = []
    current: List[str] = []
    current_len = 0

    for token in tokens:
        plain = _strip_karaoke(token)
        if current and current_len + 1 + len(plain) > max_chars and len(lines) + 1 < max_lines:
            lines.append(" ".join(current))
            current = [token]
            current_len = len(plain)
        else:
            if current:
                current_len += 1 + len(plain)
            else:
                current_len = len(plain)
            current.append(token)

    if current:
        lines.append(" ".join(current))

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    return "\\N".join(lines)


def _strip_karaoke(token: str) -> str:
    if token.startswith("{\\k"):
        end = token.find("}")
        if end != -1:
            return token[end + 1 :]
    return token


def _format_time(ms: int) -> str:
    total_seconds = ms / 1000.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def _resolve_total_duration_ms(total_duration: Optional[float], subs: pysubs2.SSAFile) -> int:
    if total_duration is not None:
        return int(max(total_duration, 0.0) * 1000)
    if subs:
        return int(max((line.end for line in subs), default=0))
    return 0


def _resolve_overlay_positions(
    overlays: Dict[str, object],
    res_x: int,
    res_y: int,
    frame: Optional[Dict[str, object]],
) -> Tuple[Optional[Dict[str, object]], Optional[Dict[str, object]]]:
    title_cfg = dict(overlays.get("title", {})) if overlays.get("title") else None
    tagline_cfg = dict(overlays.get("tagline", {})) if overlays.get("tagline") else None

    if not title_cfg and not tagline_cfg:
        return title_cfg, tagline_cfg

    padding = int(overlays.get("padding", 24))
    if frame and frame.get("mode") == "square_center":
        square_size = min(res_x, res_y)
        top = (res_y - square_size) // 2
        bottom = top + square_size

        if title_cfg is not None:
            title_padding = int(title_cfg.get("padding", padding))
            title_size = int(title_cfg.get("size", 48))
            title_cfg["alignment"] = 2
            title_cfg["margin_v"] = max((res_y - bottom) - title_padding - title_size, 0)
        if tagline_cfg is not None:
            tagline_padding = int(tagline_cfg.get("padding", padding))
            tagline_size = int(tagline_cfg.get("size", 44))
            tagline_cfg["alignment"] = 8
            tagline_cfg["margin_v"] = max(top - tagline_padding - tagline_size, 0)

    return title_cfg, tagline_cfg
