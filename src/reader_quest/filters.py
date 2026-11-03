"""Фильтрация и подписи вопросов (без зависимостей от Streamlit)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from .models import Progress, Question

STATUS_LABELS: dict[str, str] = {
    "new": "Не смотрел",
    "known": "Знаю",
    "review": "Повторить",
}


def label(question: Question) -> str:
    """Подпись вопроса для списков и виджетов."""

    return f"{question.num}. {question.title}"


def normalize_search(value: str) -> list[str]:
    return [word for word in value.lower().split() if word]


def matches_search(question: Question, words: Sequence[str]) -> bool:
    if not words:
        return True
    haystack = f"{question.title}\n{question.body}".lower()
    return all(word in haystack for word in words)


def filter_questions(
    questions: Iterable[Question],
    *,
    search: str = "",
    topics: Iterable[str] = (),
    statuses: Iterable[str] = (),
    progress: Progress | None = None,
) -> list[Question]:
    """Применяет поиск, темы и статусы. Порядок вопросов сохраняется."""

    selected_topics = set(topics)
    selected_statuses = set(statuses)
    marks = progress or Progress()
    words = normalize_search(search)

    result: list[Question] = []
    for question in questions:
        if selected_topics and not selected_topics.intersection(question.topics):
            continue
        if selected_statuses and marks.status(question.key) not in selected_statuses:
            continue
        if not matches_search(question, words):
            continue
        result.append(question)
    return result


def topic_counts(questions: Iterable[Question]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for question in questions:
        for topic in question.topics:
            counter[topic] += 1
    return counter


def status_counts(questions: Iterable[Question], progress: Progress) -> Counter[str]:
    counter: Counter[str] = Counter()
    for question in questions:
        counter[progress.status(question.key)] += 1
    return counter
