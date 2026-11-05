"""Разбор Markdown-файла с вопросами.

Исходник (407 вопросов) размечен небрежно, парсер это учитывает:

* заголовки вопросов бывают ``##``, ``#`` и даже ``##326.`` без пробела;
* номер может повторяться (267, 326) или пропускаться;
* иногда вопрос теряет разметку заголовка и остаётся строкой ``169. Вопрос?``;
* блоки ```иногда не закрыты, а одна строка содержит и открытие, и закрытие
  `` ```код``` `` — из-за этого «наивный» подсчёт сдвигает состояние и прячет
  82 вопроса внутрь кода.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import Block, Question
from .topics import classify

# Заголовок вопроса: до 6 решек, номер, точка, текст.
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s*(\d{1,3})\.\s*(.+?)\s*$")
# Тот же, но с двумя и более решками — по нему восстанавливаемся после
# незакрытого блока кода.
_STRONG_HEADER = re.compile(r"^\s{0,3}#{2,6}\s*(\d{1,3})\.\s*\S")
# Вопрос без разметки заголовка: «169. Что такое slicing в Python?»
_PLAIN_HEADER = re.compile(r"^(\d{1,3})\.\s+(\S.{2,140})$")
# Блок кода. В исходнике встречаются закрывающие ``` с отступом в 4 пробела,
# поэтому лимит CommonMark в 3 пробела слишком строгий.
_FENCE = re.compile(r"^([^\S\n]{0,7})(`{3,}|~{3,})(.*)$")

_FOOTER = re.compile(r"<div[^>]*align=[\"']?right[\"']?[^>]*>.*?</div\s*>", re.I | re.S)
_ANCHOR = re.compile(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
_IMAGE = re.compile(r"<img[^>]*/?>", re.I)
_TAGS = re.compile(r"</?(?:span|b|strong|em|i|u|sub|sup|font)\b[^>]*>", re.I)
_NBSP = re.compile(r"&nbsp;")


def _clean_text(text: str) -> str:
    """Убирает HTML-«шум» исходника, оставляя читаемый markdown."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _FOOTER.sub("", text)
    text = _ANCHOR.sub(
        lambda m: (
            m.group(2) if m.group(1) == "#" else f"[{m.group(2).strip()}]({m.group(1)})"
        ),
        text,
    )
    text = _IMAGE.sub("", text)
    text = _NBSP.sub(" ", text)
    return _TAGS.sub("", text)


def _question_key(num: int, title: str) -> str:
    digest = hashlib.sha1(title.lower().encode("utf-8")).hexdigest()[:8]
    return f"{num}-{digest}"


def split_blocks(body: str) -> tuple[Block, ...]:
    """Режет ответ на прозу и блоки кода, корректно обрабатывая ```.

    Учитываются: блоки с отступом, строка вида «```код```» (открытие и закрытие
    на одной строке) и незакрытый блок в конце ответа.
    """

    blocks: list[Block] = []
    prose: list[str] = []
    code: list[str] = []
    language = ""
    indent = ""
    in_fence = False

    def flush_prose() -> None:
        text = "\n".join(prose).strip("\n")
        if text.strip():
            blocks.append(Block("prose", text))
        prose.clear()

    def flush_code() -> None:
        text = _dedent("\n".join(code)).rstrip()
        if text.strip():
            blocks.append(Block("code", text, language or "text"))
        code.clear()

    for line in body.split("\n"):
        fence = _FENCE.match(line)
        if fence:
            marker, rest = fence.group(2), fence.group(3).strip()
            if not in_fence and rest.endswith(marker) and len(rest) > len(marker):
                # Строка «```код```»: код открывается и закрывается на одной строке.
                flush_prose()
                blocks.append(Block("code", rest[: -len(marker)].strip(), "python"))
                continue
            if in_fence:
                in_fence = False
                flush_code()
            else:
                flush_prose()
                in_fence = True
                indent = fence.group(1)
                language = rest.split()[0].lower() if rest else ""
            continue

        if in_fence:
            code.append(line[len(indent) :] if line.startswith(indent) else line)
        else:
            prose.append(line)

    if in_fence:
        flush_code()
    else:
        flush_prose()

    return tuple(blocks)


def _dedent(text: str) -> str:
    """Снимает общий отступ блоков, если он есть."""

    lines = text.split("\n")
    indents = [len(line) - len(line.lstrip(" 	")) for line in lines if line.strip()]
    if not indents or min(indents) == 0:
        return text
    shift = min(indents)
    return "\n".join(line[shift:] for line in lines)


def _trim_edges(lines: list[str]) -> str:
    """Убирает пустые строки по краям, сохраняя отступы кода."""

    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


def _nearest_nonempty(lines: list[str], start: int, step: int) -> str:
    """Ближайшая непустая строка от позиции start в направлении step."""

    index = start
    while 0 <= index < len(lines):
        stripped = lines[index].strip()
        if stripped:
            return stripped
        index += step
    return ""


def _looks_like_orphan_question(lines: list[str], index: int, title: str) -> bool:
    """Отличает потерянный заголовок вопроса от пункта нумерованного списка.

    В исходнике три вопроса остались без ``##`` («169. Что такое slicing в
    Python?»). Признак вопроса: вопросительный знак и отсутствие соседних
    нумерованных пунктов, из которых состоит список.
    """

    if not title.rstrip().endswith("?"):
        return False
    previous = _nearest_nonempty(lines, index - 1, -1)
    following = _nearest_nonempty(lines, index + 1, 1)
    if not previous:
        return False
    if _PLAIN_HEADER.match(previous) or _HEADER.match(previous):
        return False
    if not following:
        return True
    return not (_PLAIN_HEADER.match(following) or _HEADER.match(following))


def parse_questions(text: str) -> list[Question]:
    """Возвращает список вопросов из текста Markdown-файла."""

    text = _clean_text(text)
    lines = text.split("\n")

    questions: list[Question] = []
    num: int | None = None
    title = ""
    buffer: list[str] = []
    in_fence = False

    def commit() -> None:
        if num is None:
            return
        body = _trim_edges(buffer)
        questions.append(
            Question(
                key=_question_key(num, title),
                num=num,
                title=title,
                body=body,
                blocks=split_blocks(body),
                topics=classify(title, body),
            )
        )

    for index, line in enumerate(lines):
        fence = _FENCE.match(line)
        if fence:
            marker, rest = fence.group(2), fence.group(3).strip()
            single = not in_fence and rest.endswith(marker) and len(rest) > len(marker)
            if single:
                # «```код```» на одной строке — состояние не меняем.
                if num is not None:
                    buffer.append(line)
                continue
            in_fence = not in_fence
            if num is not None:
                buffer.append(line)
            continue

        header = _HEADER.match(line)
        if header and in_fence and _STRONG_HEADER.match(line):
            # Незакрытый блок кода: заголовок с двумя и более решётками
            # важнее — считаем его началом следующего вопроса.
            in_fence = False
        if header and not in_fence:
            commit()
            num = int(header.group(1))
            title = header.group(2).strip().strip("#").strip()
            buffer = []
            continue

        if not in_fence and num is not None and not line[:1].isspace():
            plain = _PLAIN_HEADER.match(line)
            if plain and _looks_like_orphan_question(lines, index, plain.group(2)):
                commit()
                num = int(plain.group(1))
                title = plain.group(2).strip()
                buffer = []
                continue

        if num is not None:
            buffer.append(line)

    commit()
    return questions


def load_questions(path: str | Path) -> list[Question]:
    """Читает файл и разбирает его в вопросы."""

    return parse_questions(Path(path).read_text(encoding="utf-8"))
