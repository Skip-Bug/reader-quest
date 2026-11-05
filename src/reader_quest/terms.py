"""Подсветка ключевых слов в текстах ответов.

Для Streamlit используются нативные markdown-директивы (``:violet[def]``,
``:blue[list]``) — цвета берутся из темы ``.streamlit/config.toml`` и совпадают
с палитрой One Dark. Для статического HTML те же категории оборачиваются в
``<span class="term-...">``.

Подсветка не трогает код в обратных кавычках, ссылки и изображения.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

_KEYWORDS: Final = (
    "def class lambda return yield import from with as pass break continue "
    "global nonlocal assert raise try except finally if elif else for while "
    "and or not in is del async await self None True False"
).split()

_TYPES: Final = (
    "int str float bool list dict set tuple complex bytes bytearray frozenset "
    "range object memoryview"
).split()

_BUILTINS: Final = (
    "print len zip map filter reduce enumerate sorted reversed sum min max abs "
    "any all id isinstance issubclass getattr setattr hasattr delattr super iter "
    "next open repr hash eval exec compile divmod round pow slice format vars dir "
    "help input ord chr bin oct hex callable"
).split()

_MODULES: Final = (
    "os sys json gc pickle copy itertools functools collections threading "
    "multiprocessing asyncio datetime typing unittest logging sqlite3 subprocess "
    "socket decimal random math time dataclasses uuid shutil pathlib"
).split()

# Понятия на кириллице и обычные слова — ищем без учёта регистра.
_CONCEPTS_CI: Final = [
    "декоратор",
    "генератор",
    "итератор",
    "замыкание",
    "сборщик мусора",
    "байткод",
    "виртуальная машина",
    "аннотация типа",
    "аннотации типов",
    "магический метод",
    "магические методы",
    "dunder",
    "list comprehension",
    "comprehension",
    "traceback",
    "stack trace",
    "docstring",
    "многопоточность",
    "асинхронность",
    "инкапсуляция",
    "полиморфизм",
    "наследование",
    "сериализация",
    "распаковка",
    "неизменяемый",
    "изменяемый",
    "глубокая копия",
    "поверхностная копия",
]

# Аббревиатуры — только с точным регистром, чтобы не красить случайные слова.
_CONCEPTS_CS: Final = [
    "GIL",
    "MRO",
    "PEP 8",
    "ООП",
    "CPython",
    "PyPy",
    "JIT",
    "ORM",
    "REST API",
    "UUID",
    "SQL",
    "HTTP",
    "JSON",
    "YAML",
    "CSV",
    "UTF-8",
    "Big O",
]

GROUPS: Final[list[tuple[str, str, list[str]]]] = [
    ("violet", "term-keyword", list(_KEYWORDS)),
    ("blue", "term-type", list(_TYPES)),
    ("green", "term-builtin", list(_BUILTINS)),
    ("orange", "term-module", list(_MODULES)),
    ("yellow", "term-concept", _CONCEPTS_CI + _CONCEPTS_CS),
]

_COLOR_TO_CLASS: Final[dict[str, str]] = {
    color_name: css_class for color_name, css_class, _ in GROUPS
}

_CS_SET: Final[frozenset[str]] = frozenset(_CONCEPTS_CS)
_CI_MAP: Final[dict[str, str]] = {}
_CS_MAP: Final[dict[str, str]] = {}
for _color, _css, _terms in GROUPS:
    for _term in _terms:
        if _term in _CS_SET:
            _CS_MAP[_term] = _color
        else:
            _CI_MAP[_term.lower()] = _color

_ALL_TERMS: Final[list[str]] = sorted(
    list(_CS_MAP) + list(_CI_MAP), key=lambda term: (-len(term), term.lower())
)
_TERM_RE: Final = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in _ALL_TERMS) + r")\b",
    re.IGNORECASE,
)

# Уже отформатированный контент: инлайн-код, ссылки, картинки — не трогаем.
_PROTECTED: Final = re.compile(r"(`[^`\n]*`)|(!?\[[^\]\n]*\]\([^)\n]*\))")

# Токены, которые выглядят как код, но не входят в словарь: *args, __dict__, globals()
# Финальный lookahead запрещает и `*`: иначе `**GIL**` распадалось бы как
# «звёздочки + идентификатор» и жирный markdown превращался в `` `**GIL`** ``.
_CODE_TOKEN: Final = re.compile(
    r"(?<![\w`*])"
    r"(?:__[A-Za-z_][A-Za-z0-9_]*__"
    r"|\*{1,2}[A-Za-z_][A-Za-z0-9_]*"
    r"|\b[A-Za-z_][A-Za-z0-9_]*\(\))(?![\w`*])"
)


def _category_of(matched: str) -> str | None:
    if matched in _CS_MAP:
        return _CS_MAP[matched]
    return _CI_MAP.get(matched.lower())


def _protect_runs(text: str) -> list[tuple[bool, str]]:
    """Разбивает текст на защищённые и обычные фрагменты."""

    runs: list[tuple[bool, str]] = []
    position = 0
    for match in _PROTECTED.finditer(text):
        if match.start() > position:
            runs.append((False, text[position : match.start()]))
        runs.append((True, match.group(0)))
        position = match.end()
    if position < len(text):
        runs.append((False, text[position:]))
    return runs


def _color_terms(text: str, render: Callable[[str, str], str]) -> str:
    parts: list[str] = []
    position = 0
    for match in _TERM_RE.finditer(text):
        category = _category_of(match.group(1))
        if category is None:
            continue
        parts.append(text[position : match.start()])
        parts.append(render(category, match.group(1)))
        position = match.end()
    if not parts:
        return text
    parts.append(text[position:])
    return "".join(parts)


def _transform_prose(
    text: str,
    render: Callable[[str, str], str],
    code_wrap: Callable[[str], str],
) -> str:
    wrapped = _CODE_TOKEN.sub(lambda m: code_wrap(m.group(0)), text)
    out: list[str] = []
    for protected, chunk in _protect_runs(wrapped):
        if protected:
            out.append(chunk)
        else:
            out.append(_color_terms(chunk, render))
    return "".join(out)


def highlight_markdown(text: str) -> str:
    """Markdown с цветными директивами Streamlit (:violet[def] и т.п.)."""

    return _transform_prose(
        text,
        render=lambda color, word: f":{color}[{word}]",
        code_wrap=lambda token: f"`{token}`",
    )


def highlight_html(text: str) -> str:
    """Markdown с css-классами категорий (для статического экспорта).

    Текст остаётся markdown-ом: ``<span>`` встраиваются в него, а обратные
    кавычки в ``markdown``-библиотеке сами превратятся в ``<code>``.
    """

    def render(color: str, word: str) -> str:
        css_class = _COLOR_TO_CLASS.get(color, "term-concept")
        return f'<span class="{css_class}">{word}</span>'

    return _transform_prose(
        text,
        render=render,
        code_wrap=lambda token: f"`{token}`",
    )
