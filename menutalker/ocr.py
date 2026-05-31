from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OCRResult:
    raw_text: str
    raw_text_path: Path
    engine_name: str
    warnings: list[str]


_PADDLE_ENGINE: Any = None


def _get_paddle_engine(lang: str) -> Any:
    global _PADDLE_ENGINE
    if _PADDLE_ENGINE is None:
        from paddleocr import PaddleOCR

        _PADDLE_ENGINE = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _PADDLE_ENGINE


def _entry_text(entry: Any) -> tuple[str, float, list[list[float]] | None] | None:
    try:
        box = entry[0]
        payload = entry[1]
        text = str(payload[0]).strip()
        confidence = float(payload[1])
        return text, confidence, box
    except (TypeError, IndexError, ValueError):
        return None


def _flatten_entries(result: Any) -> list[tuple[str, float, list[list[float]] | None]]:
    if not result:
        return []
    if len(result) == 1 and isinstance(result[0], list):
        candidate = result[0]
    else:
        candidate = result
    entries = []
    for entry in candidate:
        parsed = _entry_text(entry)
        if parsed is not None:
            entries.append(parsed)
    return entries


def _bbox_sort_key(entry: tuple[str, float, list[list[float]] | None]) -> tuple[float, float]:
    box = entry[2]
    if not box:
        return (0.0, 0.0)
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


def run_paddle_ocr(image_paths: list[Path], session_dir: Path, lang: str = "ch") -> OCRResult:
    warnings: list[str] = []
    lines: list[str] = []

    try:
        engine = _get_paddle_engine(lang)
    except Exception as exc:  # pragma: no cover - depends on optional runtime package
        warnings.append(f"PaddleOCR is unavailable: {exc}")
        raw_text_path = session_dir / "menu_raw_text.txt"
        raw_text_path.write_text("", encoding="utf-8")
        return OCRResult("", raw_text_path, "paddleocr-unavailable", warnings)

    for page_index, image_path in enumerate(image_paths, start=1):
        lines.append(f"--- Page {page_index} ---")
        try:
            result = engine.ocr(str(image_path), cls=True)
            entries = sorted(_flatten_entries(result), key=_bbox_sort_key)
        except Exception as exc:  # pragma: no cover - depends on OCR model behavior
            warnings.append(f"OCR failed on page {page_index}: {exc}")
            entries = []

        for text, confidence, _box in entries:
            if text and confidence >= 0.25:
                lines.append(text)
        lines.append("")

    raw_text = "\n".join(lines).strip()
    raw_text_path = session_dir / "menu_raw_text.txt"
    raw_text_path.write_text(raw_text, encoding="utf-8")
    return OCRResult(raw_text, raw_text_path, "paddleocr", warnings)
