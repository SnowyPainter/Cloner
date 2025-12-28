from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
import re

import pysubs2

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
) -> None:
    subs = pysubs2.load(str(srt_path))
    video = style["video"]
    res_x, res_y = video["resolution"]
    layout = style["subtitles"]["layout"]
    base = style["subtitles"]["base_style"]
    highlight = style["subtitles"]["highlight"]

    header = _build_header(res_x, res_y, layout, base, highlight, style)
    events = _build_events(subs, layout, highlight)
    if title or tagline:
        overlay = style.get("overlays", {})
        events = _prepend_overlays(events, title, tagline, overlay)

    ass_path.write_text(header + "\n" + "\n".join(events) + "\n", encoding="utf-8")


def _build_header(
    res_x: int,
    res_y: int,
    layout: Dict[str, object],
    base: Dict[str, object],
    highlight: Dict[str, object],
    style: Dict[str, object],
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

    overlays = style.get("overlays", {})
    title = overlays.get("title")
    if title:
        lines.append(
            "Style: Title,{font},{size},{primary},{secondary},{outline},{shadow},{bold},{italic},0,0,100,100,0,0,1,{outline_w},{shadow_w},{align},{margin_h},{margin_h},{margin_v},1".format(
                font=title.get("font", base["font"]),
                size=title.get("size", base["size"]),
                primary=title.get("color", primary),
                secondary=secondary,
                outline=title.get("outline_color", outline),
                shadow=title.get("shadow_color", shadow),
                bold=-1 if title.get("bold", True) else 0,
                italic=-1 if title.get("italic", False) else 0,
                outline_w=title.get("outline", base.get("outline", 3)),
                shadow_w=title.get("shadow", base.get("shadow", 2)),
                align=title.get("alignment", 8),
                margin_h=title.get("margin_h", 0),
                margin_v=title.get("margin_v", 60),
            )
        )
    tagline = overlays.get("tagline")
    if tagline:
        lines.append(
            "Style: Tagline,{font},{size},{primary},{secondary},{outline},{shadow},{bold},{italic},0,0,100,100,0,0,1,{outline_w},{shadow_w},{align},{margin_h},{margin_h},{margin_v},1".format(
                font=tagline.get("font", base["font"]),
                size=tagline.get("size", base["size"]),
                primary=tagline.get("color", primary),
                secondary=secondary,
                outline=tagline.get("outline_color", outline),
                shadow=tagline.get("shadow_color", shadow),
                bold=-1 if tagline.get("bold", True) else 0,
                italic=-1 if tagline.get("italic", False) else 0,
                outline_w=tagline.get("outline", base.get("outline", 3)),
                shadow_w=tagline.get("shadow", base.get("shadow", 2)),
                align=tagline.get("alignment", 2),
                margin_h=tagline.get("margin_h", 0),
                margin_v=tagline.get("margin_v", 80),
            )
        )

    lines += ["", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    return "\n".join(lines)


def _build_events(subs: pysubs2.SSAFile, layout: Dict[str, object], highlight: Dict[str, object]) -> List[str]:
    events: List[str] = []
    max_chars = int(layout.get("max_chars_per_line", 18))
    max_lines = int(layout.get("max_lines", 2))
    min_word = float(highlight.get("min_word_duration", 0.08))
    max_word = float(highlight.get("max_word_duration", 0.2))

    for line in subs:
        start = _format_time(line.start)
        end = _format_time(line.end)
        text = line.text.replace("\\N", " ").replace("\n", " ")
        text = re.sub(r"\[[^\]]*]", "", text).strip()
        words = [w for w in text.split() if w]
        if not words:
            continue

        duration = max((line.end - line.start) / 1000.0, 0.01)
        per_word = duration / len(words)
        per_word = max(min(per_word, max_word), min_word)
        durations = [per_word] * len(words)
        total = sum(durations)
        if total < duration:
            durations[-1] += duration - total
        elif total > duration:
            durations[-1] = max(durations[-1] - (total - duration), 0.01)

        text_with_k = _apply_karaoke(words, durations)
        text_with_k = _wrap_karaoke(text_with_k, max_chars, max_lines)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text_with_k}")

    return events


def _prepend_overlays(
    events: List[str],
    title: Optional[str],
    tagline: Optional[str],
    overlay: Dict[str, object],
) -> List[str]:
    results = list(events)
    title_cfg = overlay.get("title", {})
    tagline_cfg = overlay.get("tagline", {})
    if title:
        start = "0:00:00.00"
        end = _format_time(int(title_cfg.get("duration_ms", 3500)))
        results.insert(0, f"Dialogue: 1,{start},{end},Title,,0,0,0,,{title}")
    if tagline:
        start = "0:00:00.00"
        end = _format_time(int(tagline_cfg.get("duration_ms", 3500)))
        results.insert(0, f"Dialogue: 1,{start},{end},Tagline,,0,0,0,,{tagline}")
    return results


def _apply_karaoke(words: List[str], durations: Iterable[float]) -> str:
    parts = []
    for word, dur in zip(words, durations):
        centis = max(int(round(dur * 100)), 1)
        parts.append(f"{{\\k{centis}}}{word}")
    return " ".join(parts)


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
