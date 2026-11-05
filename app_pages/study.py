"""Страница «Изучение»: один вопрос, ответ, отметка, навигация."""

from __future__ import annotations

import streamlit as st

from reader_quest.app_helpers import (
    clear_and_save,
    ensure_revealed_reset,
    go_to,
    mark_and_save,
    neighbors,
    question_by_key,
)
from reader_quest.render import render_blocks

st.header(":material/menu_book: Изучение", anchor=False)

keys: list[str] = [q.key for q in st.session_state.visible]
if not keys:
    st.info("Под фильтры не попал ни один вопрос", title="Пусто")
    st.stop()

current = st.session_state.question if st.session_state.question in keys else keys[0]
if current != st.session_state.question:
    go_to(current)
question = question_by_key(current)
if question is None:  # pragma: no cover — защита от рассинхрона состояния
    st.stop()

ensure_revealed_reset(question.key)
position = keys.index(current) + 1
prev_key, next_key = neighbors(keys, current)

# --- Верхняя панель: навигация и счётчик ---------------------------------------
with st.container(horizontal=True):
    st.button(
        ":material/chevron_left: Назад",
        disabled=prev_key is None,
        on_click=go_to,
        args=(prev_key,),
        width="content",
    )
    st.button(
        "Вперёд :material/chevron_right:",
        disabled=next_key is None,
        on_click=go_to,
        args=(next_key,),
        width="content",
    )
    st.caption(f"**{position}** из {len(keys)}", width="stretch")

# --- Вопрос ---------------------------------------------------------------------
st.subheader(f"{question.num}. {question.title}", anchor=False)
for topic in question.topics:
    st.badge(topic, color="blue", icon=":material/tag:")

if not st.session_state.revealed:
    st.write("🤔 *Сначала ответьте в уме — потом открывайте ответ.*")
    if st.button(
        ":material/visibility: Показать ответ", type="primary", width="stretch"
    ):
        st.session_state.revealed = True
        st.rerun()
    st.stop()

# --- Ответ ----------------------------------------------------------------------
if not question.body:
    st.warning(
        "В исходном файле у этого вопроса нет текста ответа.",
        title="Ответа нет",
    )
else:
    with st.container(border=True):
        render_blocks(question.blocks)

# --- Оценка и переход -----------------------------------------------------------
with st.container(horizontal=True, horizontal_alignment="distribute"):
    if st.button(
        ":material/thumb_up: Знал",
        type="primary",
        width="content",
        help="Отметить «знаю» и перейти к следующему вопросу",
    ):
        mark_and_save(question, "known")
        # На последнем вопросе next_key нет, но перезапуск нужен, чтобы
        # обновились счётчик в сайдбаре и кнопки отметок.
        go_to(next_key or current)
    if st.button(
        ":material/replay: Повторить",
        width="content",
        help="Отметить «надо повторить» и остаться здесь",
    ):
        mark_and_save(question, "review")
        st.rerun()
    if st.button(
        ":material/undo: Сбросить отметку",
        width="content",
        disabled=st.session_state.progress.status(question.key) == "new",
        help="Убрать отметку у этого вопроса",
    ):
        clear_and_save(question)
        st.rerun()
