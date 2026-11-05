"""Страница «Экзамен»: короткая серия вопросов с самооценкой."""

from __future__ import annotations

import random

import streamlit as st

from reader_quest.app_helpers import empty_state, go_to, mark_and_save, question_by_key
from reader_quest.render import render_blocks

st.header(":material/quiz: Экзамен", anchor=False)

keys = [q.key for q in st.session_state.visible]
if not keys:
    empty_state("Под фильтры не попал ни один вопрос")

exam: dict[str, object] = st.session_state.get("exam", {})
started = bool(exam.get("queue"))


def start_exam(count: int) -> None:
    queue = random.sample(keys, min(count, len(keys)))
    st.session_state.exam = {
        "queue": queue,
        "index": 0,
        "results": {},
    }
    st.session_state.revealed = False
    st.session_state.question = queue[0]
    st.rerun()


# --- Настройка и старт ----------------------------------------------------------
if not started:
    st.write(
        "Короткая проверка себя: несколько случайных вопросов из текущей выборки. "
        "Сначала отвечаете в уме, потом сравниваете с ответом и оцениваете себя честно."
    )
    with st.container(border=True):
        count = st.slider(
            "Сколько вопросов",
            min_value=3,
            max_value=min(30, len(keys)),
            value=min(10, len(keys)),
            step=1,
        )
        if st.button(
            ":material/play_arrow: Начать экзамен", type="primary", width="stretch"
        ):
            start_exam(count)
    st.stop()

# --- Ход экзамена ----------------------------------------------------------------
queue: list[str] = exam["queue"]  # type: ignore[assignment]
index: int = exam["index"]  # type: ignore[assignment]
results: dict[str, bool] = exam["results"]  # type: ignore[assignment]

if index >= len(queue):
    correct = sum(1 for value in results.values() if value)
    st.success(
        f"Готово: {correct} из {len(queue)} правильных "
        f"({correct / len(queue):.0%} — если все вопросы были вами честно оценены).",
        title="Экзамен завершён",
    )
    st.progress(correct / len(queue) if queue else 0.0)

    if st.button(
        ":material/save: Перенести результат в прогресс",
        type="primary",
        width="stretch",
        help="Правильные — «знаю», ошибочные — «надо повторить»",
    ):
        for key, ok in results.items():
            question = question_by_key(key)
            if question is not None:
                mark_and_save(question, "known" if ok else "review")
        st.session_state.exam = {}
        st.success("Отметки сохранены", title="Готово")
        st.switch_page("app_pages/study.py")
    if st.button(":material/refresh: Пройти заново", width="stretch"):
        st.session_state.exam = {}
        st.rerun()
    st.stop()

question = question_by_key(queue[index])
if question is None:  # pragma: no cover — защита от рассинхрона
    st.error("Вопрос из очереди экзамена не найден", title="Ошибка")
    st.session_state.exam = {}
    st.stop()

st.caption(f"Вопрос {index + 1} из {len(queue)}")
st.subheader(f"{question.num}. {question.title}", anchor=False)

if not st.session_state.revealed:
    if st.button(
        ":material/visibility: Показать ответ", type="primary", width="stretch"
    ):
        st.session_state.revealed = True
        st.rerun()
    st.stop()

if not question.body:
    st.warning(
        "В исходном файле у этого вопроса нет текста ответа.",
        title="Ответа нет",
    )
else:
    with st.container(border=True):
        render_blocks(question.blocks)

st.write("Справились ли вы с вопросом?")
col_knew, col_missed = st.columns(2)
if col_knew.button(
    ":material/check_circle: Ответил верно", type="primary", width="stretch"
):
    results[question.key] = True
    exam["index"] = index + 1
    st.session_state.revealed = False
    st.session_state.exam = exam
    if index + 1 < len(queue):
        go_to(queue[index + 1])
    st.rerun()

if col_missed.button(":material/cancel: Ошибся", width="stretch"):
    results[question.key] = False
    exam["index"] = index + 1
    st.session_state.revealed = False
    st.session_state.exam = exam
    if index + 1 < len(queue):
        go_to(queue[index + 1])
    st.rerun()
