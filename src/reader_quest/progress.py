"""Сохранение прогресса между запусками в JSON-файл."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from .models import Progress

DEFAULT_DIR: Final[str] = ".reader_quest"
DEFAULT_FILE: Final[str] = "progress.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_path(root: Path | str | None = None) -> Path:
    base = Path(root) if root else Path.cwd()
    return base / DEFAULT_DIR / DEFAULT_FILE


def load(path: Path | str) -> Progress:
    """Читает прогресс; отсутствующий или битый файл не считается ошибкой."""

    file = Path(path)
    if not file.exists():
        return Progress()
    try:
        raw: dict[str, Any] = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Progress()
    marks = raw.get("marks") if isinstance(raw, dict) else None
    if not isinstance(marks, dict):
        return Progress()
    return Progress(marks={k: v for k, v in marks.items() if v in ("known", "review")})


def save(path: Path | str, progress: Progress, source: str = "") -> Path:
    """Атомарно записывает прогресс рядом с файлом приложения."""

    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated": _now(),
        "source": source,
        "marks": dict(sorted(progress.marks.items())),
    }
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=file.parent,
        prefix=".progress-",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(handle.name, file)
    finally:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
    return file
