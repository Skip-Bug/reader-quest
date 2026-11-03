"""Генерация статичного HTML из Markdown с вопросами.

По умолчанию создаётся только ``Python_Developer_Questions.html`` — автономная
страница с тёмной темой One Dark, списком вопросов, поиском и отметками в
localStorage. Приложению (``app.py``) прогонять файлы через этот скрипт
не нужно: оно парсит исходный Markdown и подсвечивает всё само.

Флагом ``--md`` дополнительно генерируется ``Python_Developer_Questions_Highlighted.md``
(подсвеченный Markdown для чтения вне приложения).

Запуск: ``python highlight.py`` (или с аргументами, см. ``--help``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reader_quest.html_export import export_html
from reader_quest.terms import highlight_html

DEFAULT_SOURCE = "Python_Developer_Questions.md"
DEFAULT_HTML = "Python_Developer_Questions.html"
DEFAULT_MD = "Python_Developer_Questions_Highlighted.md"


def build_highlighted_md(source: Path, output: Path) -> int:
    """Markdown-версия: исходный текст с <span>-подсветкой терминов."""

    questions = _load_questions(source)
    parts = []
    for question in questions:
        parts.append(f"## {question.num}. {question.title}\n")
        if question.body:
            parts.append(highlight_html(question.body))
        parts.append("")
    output.write_text("\n".join(parts), encoding="utf-8")
    return len(questions)


def _load_questions(source: Path):
    from reader_quest.parser import parse_questions

    return parse_questions(source.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input", default=DEFAULT_SOURCE, help="исходный Markdown-файл"
    )
    parser.add_argument(
        "--output-html", default=DEFAULT_HTML, help="имя HTML-результата"
    )
    parser.add_argument(
        "--output-md", default=DEFAULT_MD, help="имя подсвеченного Markdown"
    )
    parser.add_argument(
        "--md",
        action="store_true",
        help="дополнительно сгенерировать подсвеченный Markdown",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).parent
    source = Path(args.input) if Path(args.input).is_absolute() else root / args.input
    if not source.exists():
        print(f"Не найден исходный файл: {source}", file=sys.stderr)
        return 1

    questions = _load_questions(source)
    print(f"Прочитано вопросов: {len(questions)} из {source.name}")

    html_path = export_html(
        source.name,
        base_dir=source.parent,
        output=source.parent / args.output_html,
    )
    print(f"HTML готов: {html_path}")

    if args.md:
        md_output = source.parent / args.output_md
        build_highlighted_md(source, md_output)
        print(f"Markdown готов: {md_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
