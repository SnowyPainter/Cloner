from __future__ import annotations

import html
import logging
import re
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

import pysubs2

CJK_LANGS = {"zh", "ja", "ko"}


def target_srt_path(subtitles_dir: Path, target_lang: str) -> Path:
    normalized = _normalize_lang_code(target_lang)
    safe = normalized.replace("-", "_")
    return subtitles_dir / f"translated_{safe}.srt"


def translate_srt(
    srt_path: Path,
    output_path: Path,
    target_lang: str,
    source_lang: Optional[str] = None,
    batch_size: int = 8,
    audio_path: Optional[Path] = None,
    whisper_model: str = "small",
) -> Path:
    if output_path.exists():
        return output_path
    if not srt_path.exists():
        raise FileNotFoundError(f"Missing source subtitles: {srt_path}")

    normalized_target = _normalize_lang_code(target_lang)
    normalized_source = _normalize_lang_code(source_lang) if source_lang else None

    subs = None
    used_whisper = False
    if audio_path:
        try:
            subs = _translate_with_whisper(audio_path, normalized_target, whisper_model)
            normalized_source = "en"
            used_whisper = True
        except Exception as exc:
            logging.warning("faster-whisper translation failed; falling back to Argos: %s", exc)
            subs = None

    if subs is None:
        subs = pysubs2.load(str(srt_path))
        if not normalized_source:
            normalized_source = _detect_source_lang(_collect_sample_texts(subs))

    if normalized_source == normalized_target:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if used_whisper:
            for event in subs:
                text = _normalize_event_text(event.text)
                if text:
                    event.text = _postprocess_text(text, normalized_target).replace("\n", r"\N")
            subs.save(str(output_path), format_="srt")
        else:
            shutil.copyfile(srt_path, output_path)
        return output_path

    src_code = _resolve_argos_code(normalized_source)
    tgt_code = _resolve_argos_code(normalized_target)
    logging.info(
        "Translating subtitles with Argos Translate (src=%s tgt=%s)",
        src_code,
        tgt_code,
    )

    translations = _translate_lines_argos(
        [text for text in _iter_event_texts(subs) if text],
        src_code=src_code,
        tgt_code=tgt_code,
        batch_size=batch_size,
    )

    translated_iter = iter(translations)
    for event in subs:
        text = _normalize_event_text(event.text)
        if not text:
            continue
        translated = next(translated_iter)
        processed = _postprocess_text(translated, normalized_target)
        event.text = processed.replace("\n", r"\N")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path), format_="srt")
    return output_path


def _resolve_argos_code(lang: str) -> str:
    key = _normalize_lang_code(lang)
    if key.startswith("zh"):
        return "zh"
    return key


def _translate_lines_argos(
    lines: List[str],
    src_code: str,
    tgt_code: str,
    batch_size: int = 8,
) -> List[str]:
    if not lines:
        return []
    try:
        from argostranslate import package, translate
    except Exception as exc:
        raise RuntimeError("argostranslate is required for subtitle translation") from exc

    _ensure_argos_package(src_code, tgt_code, package, translate)
    installed_languages = translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == src_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == tgt_code), None)
    if not from_lang or not to_lang:
        raise RuntimeError(f"Argos Translate language not installed: {src_code}->{tgt_code}")
    translator = from_lang.get_translation(to_lang)
    if translator is None:
        raise RuntimeError(f"Argos Translate package missing for {src_code}->{tgt_code}")

    results: List[str] = []
    for batch in _chunks(lines, batch_size):
        results.extend(translator.translate(line) for line in batch)
    return results


def _translate_with_whisper(
    video_path: Path,
    target_lang: str,
    model: str,
) -> pysubs2.SSAFile:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise RuntimeError("faster-whisper package is required for audio translation") from exc

    task = "translate"
    if target_lang != "en":
        logging.info("Whisper translate outputs English only; will translate to %s with Argos", target_lang)

    whisper_model = WhisperModel(model, device="cpu", compute_type="int8")
    segments, _info = whisper_model.transcribe(str(video_path), task=task)

    subs = pysubs2.SSAFile()
    for segment in segments:
        start = int(round(float(getattr(segment, "start", 0.0)) * 1000.0))
        end = int(round(float(getattr(segment, "end", 0.0)) * 1000.0))
        text = str(getattr(segment, "text", "")).strip()
        subs.append(pysubs2.SSAEvent(start=start, end=end, text=text))
    return subs


def _ensure_argos_package(src_code: str, tgt_code: str, package, translate) -> None:
    try:
        get_translation_from_codes = getattr(translate, "get_translation_from_codes", None)
        if get_translation_from_codes and get_translation_from_codes(src_code, tgt_code):
            return
    except Exception:
        pass

    installed = translate.get_installed_languages()
    for lang in installed:
        if lang.code != src_code:
            continue
        try:
            if lang.get_translation(tgt_code):
                return
        except Exception:
            continue

    available = package.get_available_packages()
    match = next(
        (pkg for pkg in available if pkg.from_code == src_code and pkg.to_code == tgt_code),
        None,
    )
    if not match:
        raise RuntimeError(f"No Argos Translate package for {src_code}->{tgt_code}")
    package.install_from_path(match.download())


def _iter_event_texts(subs: Iterable[pysubs2.SSAEvent]) -> Iterable[str]:
    for event in subs:
        text = _normalize_event_text(event.text)
        if text:
            yield text


def _normalize_event_text(text: str) -> str:
    return text.replace(r"\N", "\n").strip()


def _collect_sample_texts(subs: Iterable[pysubs2.SSAEvent], limit: int = 50) -> str:
    collected: List[str] = []
    for text in _iter_event_texts(subs):
        collected.append(text)
        if len(collected) >= limit:
            break
    return " ".join(collected)


def _detect_source_lang(sample_text: str) -> str:
    if not sample_text:
        return "en"
    for ch in sample_text:
        codepoint = ord(ch)
        if _is_hangul(codepoint):
            return "ko"
        if _is_hiragana(codepoint) or _is_katakana(codepoint):
            return "ja"
        if _is_cjk(codepoint):
            return "zh"
        if _is_cyrillic(codepoint):
            return "ru"
        if _is_greek(codepoint):
            return "el"
        if _is_arabic(codepoint):
            return "ar"
        if _is_hebrew(codepoint):
            return "he"
        if _is_devanagari(codepoint):
            return "hi"
    return "en"


def _normalize_lang_code(lang: Optional[str]) -> str:
    if not lang:
        return "en"
    cleaned = lang.strip().lower().replace("_", "-")
    if cleaned.startswith("zh-") or cleaned in {"zh-cn", "zh-hans", "zh-hant", "zh-tw", "zh-hk"}:
        return cleaned
    if cleaned.startswith("pt-"):
        return "pt"
    if cleaned.startswith("en-"):
        return "en"
    return cleaned.split("-", 1)[0]


def _postprocess_text(text: str, target_lang: str) -> str:
    cleaned = html.unescape(text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    if target_lang not in CJK_LANGS:
        cleaned = re.sub(r"([,.!?;:])([^\s])", r"\1 \2", cleaned)
    cleaned = re.sub(r"\s+([)\]])", r"\1", cleaned)
    cleaned = re.sub(r"([(\[])\s+", r"\1", cleaned)
    return cleaned


def _chunks(items: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _is_hangul(codepoint: int) -> bool:
    return 0xAC00 <= codepoint <= 0xD7A3


def _is_hiragana(codepoint: int) -> bool:
    return 0x3040 <= codepoint <= 0x309F


def _is_katakana(codepoint: int) -> bool:
    return 0x30A0 <= codepoint <= 0x30FF


def _is_cjk(codepoint: int) -> bool:
    return 0x4E00 <= codepoint <= 0x9FFF


def _is_cyrillic(codepoint: int) -> bool:
    return 0x0400 <= codepoint <= 0x04FF


def _is_greek(codepoint: int) -> bool:
    return 0x0370 <= codepoint <= 0x03FF


def _is_arabic(codepoint: int) -> bool:
    return 0x0600 <= codepoint <= 0x06FF


def _is_hebrew(codepoint: int) -> bool:
    return 0x0590 <= codepoint <= 0x05FF


def _is_devanagari(codepoint: int) -> bool:
    return 0x0900 <= codepoint <= 0x097F
