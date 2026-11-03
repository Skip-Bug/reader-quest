"""Хелперы для страниц Streamlit-приложения (app_pages/*.py)."""

from __future__ import annotations

import streamlit as st

from .models import Progress, Question, Status
from .progress import save as save_progress


def go_to(key: str, *, reset_answer: bool = True) -> None:
    """Переключает текущий вопрос и перезапускает приложение."""

    st.session_state.question = key
    if reset_answer:
        st.session_state.revealed = False
    st.rerun()


def neighbors(keys: list[str], key: str) -> tuple[str | None, str | None]:
    """Соседние ключи в списке: (предыдущий, следующий) с зацикливанием."""

    if not keys:
        return None, None
    try:
        index = keys.index(key)
    except ValueError:
        return keys[-1], keys[0]
    return keys[index - 1], keys[(index + 1) % len(keys)]


def mark_and_save(question: Question, status: Status) -> None:
    """Ставит отметку и сразу пишет прогресс на диск."""

    progress: Progress = st.session_state.progress
    progress.marks[question.key] = status
    save_progress(
        st.session_state.progress_path, progress, st.session_state.source_name
    )


def ensure_revealed_reset(question_key: str) -> None:
    """Сбрасывает «ответ показан» при смене вопроса."""

    last = st.session_state.get("last_seen_question")
    if last != question_key:
        st.session_state.last_seen_question = question_key
        st.session_state.revealed = False


def question_by_key(key: str) -> Question | None:
    for question in st.session_state.questions:
        if question.key == key:
            return question
    return None


def empty_state(message: str) -> None:
    """Заглушка, когда фильтры ничего не вернули."""

    st.info(message, title="Пусто", icon=":material/filter_alt_off:")
    st.caption("Ослабьте фильтры в сайдбаре или выберите другой файл.")
    st.stop()
