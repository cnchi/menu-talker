from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")


@dataclass
class OCRResult:
    raw_text: str
    raw_text_path: Path
    engine_name: str
    warnings: list[str]


_PADDLE_ENGINES: dict[str, Any] = {}


def _get_paddle_engine(lang: str) -> Any:
    if lang not in _PADDLE_ENGINES:
        from paddleocr import PaddleOCR

        attempts = [
            {
                "lang": lang,
                "use_textline_orientation": True,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "enable_mkldnn": False,
            },
            {"lang": lang, "use_textline_orientation": True, "enable_mkldnn": False},
            {"lang": lang, "use_angle_cls": True, "enable_mkldnn": False},
            {"lang": lang, "enable_mkldnn": False},
            {"lang": lang, "use_textline_orientation": True},
            {"lang": lang, "use_angle_cls": True},
            {"lang": lang},
        ]
        errors = []
        for kwargs in attempts:
            try:
                _PADDLE_ENGINES[lang] = PaddleOCR(**kwargs)
                break
            except (TypeError, ValueError) as exc:
                errors.append(f"{kwargs}: {exc}")
        else:
            raise RuntimeError("; ".join(errors))
    return _PADDLE_ENGINES[lang]


def _entry_text(entry: Any) -> tuple[str, float, list[list[float]] | None] | None:
    try:
        box = entry[0]
        payload = entry[1]
        text = str(payload[0]).strip()
        confidence = float(payload[1])
        return text, confidence, box
    except (TypeError, IndexError, ValueError):
        return None


def _dict_entries(result: dict[str, Any]) -> list[tuple[str, float, list[list[float]] | None]]:
    if "res" in result and isinstance(result["res"], dict):
        return _dict_entries(result["res"])

    texts = result.get("rec_texts") or result.get("texts")
    if not isinstance(texts, list):
        return []

    scores = result.get("rec_scores") or result.get("scores") or []
    boxes = result.get("rec_polys") or result.get("dt_polys") or result.get("rec_boxes") or []
    entries = []
    for index, text in enumerate(texts):
        cleaned = str(text).strip()
        if not cleaned:
            continue
        try:
            confidence = float(scores[index]) if index < len(scores) else 1.0
        except (TypeError, ValueError):
            confidence = 1.0
        box = boxes[index] if index < len(boxes) else None
        entries.append((cleaned, confidence, box))
    return entries


def _object_entries(result: Any) -> list[tuple[str, float, list[list[float]] | None]]:
    if hasattr(result, "res") and isinstance(result.res, dict):
        return _dict_entries(result.res)
    json_payload = getattr(result, "json", None)
    if callable(json_payload):
        try:
            payload = json_payload()
        except Exception:
            return []
        if isinstance(payload, dict):
            return _dict_entries(payload)
    return []


def _flatten_entries(result: Any) -> list[tuple[str, float, list[list[float]] | None]]:
    if not result:
        return []

    if isinstance(result, dict):
        return _dict_entries(result)

    object_entries = _object_entries(result)
    if object_entries:
        return object_entries

    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
        candidate = result[0]
    else:
        candidate = result

    entries = []
    for entry in candidate:
        if isinstance(entry, dict):
            entries.extend(_dict_entries(entry))
            continue
        object_entries = _object_entries(entry)
        if object_entries:
            entries.extend(object_entries)
            continue
        parsed = _entry_text(entry)
        if parsed is not None:
            entries.append(parsed)
    return entries


def _run_ocr(engine: Any, image_path: Path) -> Any:
    predict = getattr(engine, "predict", None)
    if callable(predict):
        try:
            return predict(str(image_path))
        except TypeError:
            pass

    try:
        return engine.ocr(str(image_path), cls=True)
    except TypeError as exc:
        if "cls" not in str(exc):
            raise
        return engine.ocr(str(image_path))


def _bbox_sort_key(entry: tuple[str, float, list[list[float]] | None]) -> tuple[float, float]:
    box = entry[2]
    if box is None:
        return (0.0, 0.0)
    if hasattr(box, "tolist"):
        box = box.tolist()
    if not box:
        return (0.0, 0.0)
    if len(box) == 4 and all(isinstance(value, (int, float)) for value in box):
        x1, y1, x2, y2 = box
        box = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    xs = [point[0] for point in box if len(point) >= 2]
    ys = [point[1] for point in box if len(point) >= 2]
    if not xs or not ys:
        return (0.0, 0.0)
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
            result = _run_ocr(engine, image_path)
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
