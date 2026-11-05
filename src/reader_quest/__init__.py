"""reader-quest: ядро приложения для подготовки к Python-собеседованиям.

Модули:

* :mod:`reader_quest.parser` — разбор Markdown в вопросы;
* :mod:`reader_quest.terms` — подсветка ключевых слов;
* :mod:`reader_quest.topics` — автоматическая рубрикация по темам;
* :mod:`reader_quest.progress` — сохранение отметок «знаю / повторить»;
* :mod:`reader_quest.html_export` — автономный HTML-файл для чтения офлайн.
"""

from __future__ import annotations

from .filters import filter_questions, label, status_counts, topic_counts
from .models import Block, Progress, Question, Status
from .parser import load_questions, parse_questions, split_blocks
from .terms import GROUPS, highlight_html, highlight_markdown
from .topics import ALL_TOPICS, classify

__all__ = [
    "ALL_TOPICS",
    "GROUPS",
    "Block",
    "Progress",
    "Question",
    "Status",
    "classify",
    "filter_questions",
    "highlight_html",
    "highlight_markdown",
    "label",
    "load_questions",
    "parse_questions",
    "split_blocks",
    "status_counts",
    "topic_counts",
]
