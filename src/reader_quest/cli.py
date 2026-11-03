"""CLI reader-quest: запуск приложения и генерация статичного HTML.

Команды (по умолчанию ``run``):

* ``run``   — запускает Streamlit-приложение;
* ``build`` — генерирует ``Python_Developer_Questions.html``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .html_export import export_html

DEFAULT_SOURCE = "Python_Developer_Questions.md"


def _root() -> Path:
    # Файл лежит в src/reader_quest/, корень проекта — на три уровня выше.
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reader-quest",
        description="Тренажёр подготовки к собеседованиям по Python.",
    )
    parser.add_argument(
        "command", nargs="?", choices=("run", "build"), default="run"
    )
    args = parser.parse_args(argv)

    root = _root()
    app = root / "app.py"
    if not app.exists():
        print(f"Не найден {app}. Запускайте из папки проекта.", file=sys.stderr)
        return 1

    if args.command == "run":
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(app)],
            cwd=root,
        )

    output = export_html(DEFAULT_SOURCE, base_dir=root)
    print(f"HTML готов: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
