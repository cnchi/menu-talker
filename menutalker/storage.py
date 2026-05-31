from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def storage_root() -> Path:
    configured = os.getenv("MENUTALKER_STORAGE_DIR")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path("/data/menutalker"))
    candidates.append(Path(tempfile.gettempdir()) / "menutalker")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue

    fallback = Path(tempfile.mkdtemp(prefix="menutalker_"))
    return fallback


def new_session_dir() -> Path:
    path = storage_root() / f"session_{uuid.uuid4().hex[:12]}"
    path.mkdir(parents=True, exist_ok=True)
    (path / "images").mkdir(exist_ok=True)
    (path / "processed").mkdir(exist_ok=True)
    return path


def read_project_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
