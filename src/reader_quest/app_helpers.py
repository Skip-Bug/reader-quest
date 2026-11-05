"""Хелперы для страниц Streamlit-приложения (app_pages/*.py)."""

from __future__ import annotations

import streamlit as st

from .models import Progress, Question, Status
from .progress import save as save_progress


def go_to(key: str | None, *, reset_answer: bool = True) -> None:
    """Переключает текущий вопрос и перезапускает приложение.

    ``None`` (край выборки) игнорируется: вызов из обработчика кнопки,
    которая на краях недоступна.
    """

    if key is None:
        return
    st.session_state.question = key
    if reset_answer:
        st.session_state.revealed = False
    st.rerun()


def neighbors(keys: list[str], key: str) -> tuple[str | None, str | None]:
    """Соседние ключи в списке: (предыдущий, следующий).

    Без зацикливания: на краях выборки возвращается ``None``, поэтому
    кнопки «Назад»/«Вперёд» можно честно отключать.
    """

    if not keys:
        return None, None
    try:
        index = keys.index(key)
    except ValueError:
        return None, keys[0]
    prev_key = keys[index - 1] if index > 0 else None
    next_key = keys[index + 1] if index + 1 < len(keys) else None
    return prev_key, next_key


def mark_and_save(question: Question, status: Status) -> None:
    """Ставит отметку и сразу пишет прогресс на диск."""

    progress: Progress = st.session_state.progress
    progress.marks[question.key] = status
    save_progress(
        st.session_state.progress_path, progress, st.session_state.source_name
    )


def clear_and_save(question: Question) -> None:
    """Снимает отметку и сразу пишет прогресс на диск."""

    progress: Progress = st.session_state.progress
    progress.reset(question.key)
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
    questions: list[Question] = st.session_state.questions
    for question in questions:
        if question.key == key:
            return question
    return None


def empty_state(message: str) -> None:
    """Заглушка, когда фильтры ничего не вернули."""

    st.info(message, title="Пусто", icon=":material/filter_alt_off:")
    st.caption("Ослабьте фильтры в сайдбаре или выберите другой файл.")
    st.stop()
