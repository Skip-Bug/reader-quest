"""Отрисовка блоков ответа в Streamlit.

Проза идёт через ``st.markdown`` с подсветкой терминов, код — через
``st.code`` со встроенной подсветкой синтаксиса. Никакого кастомного CSS:
цвета берутся из темы ``.streamlit/config.toml``.
"""

from __future__ import annotations

import streamlit as st

from .models import Block
from .terms import highlight_markdown

# В исходнике один и тот же язык подписан по-разному.
_LANGUAGE_ALIASES: dict[str, str | None] = {
    "py": "python",
    "python": "python",
    "python3": "python",
    "py3": "python",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "console": "bash",
    "c++": "cpp",
    "cpp": "cpp",
    "java": "java",
    "javascript": "javascript",
    "json": "json",
    "html": "html",
    "sql": "sql",
    "yaml": "yaml",
    "text": None,
    "": None,
}


def normalize_language(language: str) -> str | None:
    key = (language or "").strip().lower()
    return _LANGUAGE_ALIASES.get(key, key or None)


def render_blocks(blocks: tuple[Block, ...] | list[Block]) -> None:
    """Рендерит блоки ответа: текст и код."""

    for block in blocks:
        if block.kind == "code":
            st.code(
                block.text,
                language=normalize_language(block.language),
                line_numbers=len(block.text.splitlines()) > 1,
                wrap_lines=True,
            )
        else:
            st.markdown(highlight_markdown(block.text))
