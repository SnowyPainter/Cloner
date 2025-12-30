from __future__ import annotations

import html
import logging
import re
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

import pysubs2

CJK_LANGS = {"zh", "ja", "ko"}
MODEL_NAME = "facebook/nllb-200-distilled-600M"

LANG_MAP = {
    "en": "eng_Latn",
    "ko": "kor_Hang",
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",
    "zh-hans": "zho_Hans",
    "zh-cn": "zho_Hans",
    "zh-tw": "zho_Hant",
    "zh-hk": "zho_Hant",
    "zh-hant": "zho_Hant",
    "ru": "rus_Cyrl",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "pt": "por_Latn",
    "it": "ita_Latn",
    "vi": "vie_Latn",
    "th": "tha_Thai",
    "id": "ind_Latn",
    "ar": "ara_Arab",
    "hi": "hin_Deva",
    "tr": "tur_Latn",
}


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
) -> Path:
    if output_path.exists():
        return output_path
    if not srt_path.exists():
        raise FileNotFoundError(f"Missing source subtitles: {srt_path}")

    normalized_target = _normalize_lang_code(target_lang)
    normalized_source = _normalize_lang_code(source_lang) if source_lang else None

    subs = pysubs2.load(str(srt_path))
    if not normalized_source:
        normalized_source = _detect_source_lang(_collect_sample_texts(subs))

    if normalized_source == normalized_target:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(srt_path, output_path)
        return output_path

    src_code = _resolve_nllb_code(normalized_source)
    tgt_code = _resolve_nllb_code(normalized_target)
    logging.info(
        "Translating subtitles with NLLB model=%s (src=%s tgt=%s)",
        MODEL_NAME,
        src_code,
        tgt_code,
    )

    translations = _translate_lines_nllb(
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


def _resolve_nllb_code(lang: str) -> str:
    key = _normalize_lang_code(lang)
    if key in LANG_MAP:
        return LANG_MAP[key]
    raise ValueError(f"Unsupported language code for NLLB: {lang}")


def _translate_lines_nllb(
    lines: List[str],
    src_code: str,
    tgt_code: str,
    batch_size: int = 8,
) -> List[str]:
    if not lines:
        return []
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:
        raise RuntimeError(
            "transformers, torch, and sentencepiece are required for NLLB translation"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    tokenizer.src_lang = src_code
    forced_bos = tokenizer.convert_tokens_to_ids(tgt_code)

    results: List[str] = []
    for batch in _chunks(lines, batch_size):
        tokens = tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(device)
        with torch.no_grad():
            generated = model.generate(
                **tokens,
                forced_bos_token_id=forced_bos,
                max_new_tokens=128,
                num_beams=4,
            )
        results.extend(tokenizer.batch_decode(generated, skip_special_tokens=True))
    return results


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
