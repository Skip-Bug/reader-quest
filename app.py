"""reader-quest — подготовка к собеседованиям по Python.

Запуск: ``streamlit run app.py``
"""

from __future__ import annotations

import random
from pathlib import Path

import streamlit as st

from reader_quest.filters import STATUS_LABELS, filter_questions, topic_counts
from reader_quest.models import Progress, Question
from reader_quest.progress import default_path, load, save
from reader_quest.sources import discover_and_parse
from reader_quest.topics import TOPIC_RULES

APP_DIR = Path(__file__).parent

st.set_page_config(
    page_title="Python собеседование: вопросы и ответы",
    page_icon=":material/school:",
    layout="centered",
)


def sync_question() -> None:
    """Переносит выбор из виджета в логический указатель текущего вопроса."""

    st.session_state.question = st.session_state.question_picker
    st.session_state.revealed = False


@st.dialog("Сбросить все отметки?", icon=":material/delete:")
def confirm_reset(source: str, total: int) -> None:
    """Диалог подтверждения: сброс удаляет отметки без возможности отменить."""

    st.write(
        f"Будут удалены все отметки «Знал» и «Повторить» у {total} вопросов "
        f"из файла `{source}`. Отменить это нельзя."
    )
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        st.button("Отмена", on_click=st.rerun, width="content")
        if st.button("Да, сбросить", type="primary", width="content"):
            st.session_state.progress = Progress()
            save(st.session_state.progress_path, st.session_state.progress, source)
            st.rerun()


def file_fingerprints() -> tuple[tuple[str, float], ...]:
    """mtime-отпечатки md-файлов: участвуют в ключе кэша, чтобы приложение
    перечитало данные после изменения файлов."""

    return tuple(
        (file.name, file.stat().st_mtime) for file in sorted(APP_DIR.glob("*.md"))
    )


@st.cache_data(show_spinner="Читаю файлы с вопросами…")
def load_all(fingerprints: tuple[tuple[str, float], ...]) -> dict[str, list[Question]]:
    """Парсит все подходящие md-файлы и дедуплицирует дубликаты."""

    del fingerprints
    return discover_and_parse(APP_DIR)


# --- Состояние сессии ----------------------------------------------------------
if "progress_path" not in st.session_state:
    st.session_state.progress_path = default_path(APP_DIR)
if "progress" not in st.session_state:
    st.session_state.progress = load(st.session_state.progress_path)

sources_by_file = load_all(file_fingerprints())
if not sources_by_file:
    st.error("Не нашёл Markdown-файлы с вопросами", title="Нет данных")
    st.caption(
        f"Приложение ищет в `{APP_DIR}` файлы `*.md`, где не меньше 20 "
        "заголовков вида `## 1. Вопрос`."
    )
    st.stop()

# --- Сайдбар: источник, фильтры, прогресс --------------------------------------
with st.sidebar:
    st.header(":material/school: Подготовка к собеседованию")

    # Без bind="query-params": switch_page очищает query-параметры и падает
    # на связанных с виджетами значениях (StreamlitAPIException).
    source = st.selectbox(
        "Файл с вопросами",
        list(sources_by_file),
        key="source",
        help="Дубликаты с одинаковым содержимым показаны один раз.",
    )
    source = str(source)
    questions = sources_by_file[source]
    labels = {q.key: f"{q.num}. {q.title}" for q in questions}

    counts = topic_counts(questions)
    available_topics = [topic for topic, _ in TOPIC_RULES if topic in counts]
    if "Разное" in counts:
        available_topics.append("Разное")

    st.text_input(
        ":material/search: Поиск",
        key="search",
        placeholder="GIL, декоратор, isinstance…",
    )

    # Отложенный фильтр со страницы «Статистика» («Учить эту тему») можно
    # записать в ключ виджета только ДО его создания в этом прогоне — иначе
    # Streamlit поднимает StreamlitWidgetAlreadyInstantiatedError.
    pending_topics = st.session_state.pop("pending_topics", None)
    if pending_topics is not None:
        st.session_state.topics = pending_topics

    st.multiselect("Темы", available_topics, key="topics")
    st.pills(
        "Статус",
        ["new", "known", "review"],
        selection_mode="multi",
        format_func=lambda value: STATUS_LABELS[str(value)],
        key="statuses",
        help="Отметки со страниц «Изучение» и «Экзамен».",
    )
    st.toggle(":material/code: Только с кодом", key="only_code")
    order = st.segmented_control(
        "Порядок",
        ["По номеру", "По теме", "Перемешать"],
        default="По номеру",
        key="order",
        width="stretch",
    )

    visible = filter_questions(
        questions,
        search=str(st.session_state.search),
        topics=list(st.session_state.topics),
        statuses=list(st.session_state.statuses),
        progress=st.session_state.progress,
    )
    if st.session_state.only_code:
        visible = [q for q in visible if q.has_code]

    if order == "По теме":
        visible = sorted(visible, key=lambda q: (q.topics[0], q.num))
    elif order == "Перемешать":
        seed = st.session_state.setdefault("shuffle_seed", random.randrange(10**6))
        visible = sorted(visible, key=lambda q: hash((seed, q.key)))

    total = len(questions)
    known = sum(
        1 for q in questions if st.session_state.progress.status(q.key) == "known"
    )
    review = sum(
        1 for q in questions if st.session_state.progress.status(q.key) == "review"
    )
    st.progress(
        known / total if total else 0.0,
        text=f"Знаю {known} из {total} · на повторе {review}",
    )

    if not visible:
        st.warning("Под фильтры не попал ни один вопрос")

    keys = [q.key for q in visible]
    if "question" not in st.session_state or st.session_state.question not in keys:
        st.session_state.question = keys[0] if keys else None
    if keys:
        # Значение виджета выставляем до его создания; после создания ключ
        # менять нельзя, поэтому логический указатель хранится отдельно.
        st.session_state.question_picker = st.session_state.question
        st.selectbox(
            "Вопрос",
            keys,
            key="question_picker",
            format_func=lambda key: labels[str(key)],
            on_change=sync_question,
        )

    if st.button(":material/shuffle: Случайный вопрос", width="stretch") and keys:
        st.session_state.question = random.choice(keys)
        st.session_state.revealed = False
        st.rerun()

    with st.expander(":material/settings: Прогресс и файлы"):
        st.caption(f"Отметки: `{st.session_state.progress_path}`")
        st.json(st.session_state.progress.counts(), expanded=False)
        if st.button(":material/delete: Сбросить отметки", width="stretch"):
            confirm_reset(source, total)

# --- Общие данные для страниц --------------------------------------------------
st.session_state.questions = questions
st.session_state.visible = visible
st.session_state.labels = labels
st.session_state.source_name = source
st.session_state.app_dir = APP_DIR

page = st.navigation(
    {
        "Подготовка": [
            st.Page(
                "app_pages/study.py",
                title="Изучение",
                icon=":material/menu_book:",
                default=True,
            ),
            st.Page("app_pages/exam.py", title="Экзамен", icon=":material/quiz:"),
        ],
        "Прогресс": [
            st.Page(
                "app_pages/stats.py", title="Статистика", icon=":material/analytics:"
            ),
        ],
    }
)
page.run()
