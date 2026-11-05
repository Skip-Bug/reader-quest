"""Поиск Markdown-файлов с вопросами и дедупликация дубликатов.

В проекте могут лежать копии одного и того же сборника (например
``Python_Developer_Questions.md`` и «400 вопросов с ответами….md», различающиеся
рекламным подвалом, который парсер всё равно вырезает). Чтобы не показывать
пользователю два одинаковых источника, файлы сравниваются по результату
парсинга: вопросы и ответы.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from .models import Question
from .parser import parse_questions

# Результат работы highlight.py: приложение не должно предлагать его
# как источник — подсветку UI делает сам.
GENERATED_MD: str = "Python_Developer_Questions_Highlighted.md"

_HEADER_HINT = re.compile(r"^#{1,6}\s*\d{1,3}\.", re.MULTILINE)


def _content_id(questions: Sequence[Question]) -> str:
    """Стабильный слепок содержимого: номера, заголовки и тексты ответов."""

    digest = hashlib.sha1()
    for question in questions:
        digest.update(
            f"{question.num}\x00{question.title}\x00{question.body}".encode()
        )
    return digest.hexdigest()


def _priority(item: tuple[str, Sequence[Question]]) -> tuple[int, int, int, str]:
    """Порядок приоритета источников.

    Больше вопросов — выше; при равенстве побеждает имя без не-ASCII
    символов (каноничные ``Python_Developer_Questions.md`` вместо
    человеческих копий «400 вопросов….md»), затем более короткое имя,
    затем алфавит.
    """

    name, questions = item
    non_ascii = sum(1 for ch in name if ord(ch) > 127)
    return (-len(questions), non_ascii, len(name), name)


def discover_and_parse(
    directory: Path,
    *,
    min_questions: int = 20,
    excluded: Iterable[str] = (GENERATED_MD,),
) -> dict[str, list[Question]]:
    """Находит подходящие ``*.md`` в папке и дедуплицирует по содержимому.

    Возвращает словарь «имя файла -> вопросы» в порядке приоритета:
    дубликаты (одинаковое содержимое после парсинга) оставляют одну запись.
    """

    skipped = set(excluded)
    candidates: list[tuple[str, list[Question]]] = []
    for file in sorted(directory.glob("*.md")):
        if file.name in skipped:
            continue
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(_HEADER_HINT.findall(text)) < min_questions:
            continue
        candidates.append((file.name, parse_questions(text)))

    candidates.sort(key=_priority)

    result: dict[str, list[Question]] = {}
    seen: set[str] = set()
    for name, questions in candidates:
        content_id = _content_id(questions)
        if content_id in seen:
            continue
        seen.add(content_id)
        result[name] = questions
    return result
