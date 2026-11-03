"""Страница «Статистика»: прогресс по темам и слабые места."""

from __future__ import annotations

import streamlit as st

from reader_quest.app_helpers import empty_state
from reader_quest.models import Progress, Question

st.header(":material/analytics: Статистика", anchor=False)

questions: list[Question] = st.session_state.questions
progress: Progress = st.session_state.progress
if not questions:
    empty_state("Файл с вопросами пуст")

total = len(questions)
known = sum(1 for q in questions if progress.status(q.key) == "known")
review = sum(1 for q in questions if progress.status(q.key) == "review")
fresh = total - known - review

cols = st.columns(4)
cols[0].metric("Всего вопросов", total)
cols[1].metric("Знаю", known, f"+{known}" if known else None)
cols[2].metric("Надо повторить", review)
cols[3].metric("Не смотрел", fresh)

st.progress(
    known / total if total else 0.0,
    text=f"Освоено {known / total:.0%}" if total else "0%",
)

# --- Разбивка по темам ------------------------------------------------------------
st.subheader("По темам", anchor=False)

topic_stats: dict[str, dict[str, int]] = {}
for question in questions:
    for topic in question.topics:
        stats = topic_stats.setdefault(topic, {"total": 0, "known": 0, "review": 0})
        stats["total"] += 1
        status = progress.status(question.key)
        if status == "known":
            stats["known"] += 1
        elif status == "review":
            stats["review"] += 1

# «Слабые» темы: больше всего непокрытых вопросов (новые + на повторе).
rows = []
for topic, stats in topic_stats.items():
    uncovered = stats["total"] - stats["known"]
    rows.append(
        {
            "Тема": topic,
            "Вопросов": stats["total"],
            "Знаю": stats["known"],
            "Повторить": stats["review"],
            "Не освоено": uncovered,
            "Доля известных": stats["known"] / stats["total"]
            if stats["total"]
            else 0.0,
        }
    )
rows.sort(key=lambda row: (-row["Не освоено"], row["Тема"]))

st.caption("Слабые темы сверху: сначала там, где больше вопросов без отметки «знаю».")
for row in rows:
    share = row["Доля известных"]
    with st.container(border=True):
        top = st.container(horizontal=True, vertical_alignment="center")
        top.markdown(f"**{row['Тема']}**", width="stretch")
        top.caption(
            f"{row['Знаю']}/{row['Вопросов']} знаю · повторить: {row['Повторить']}"
        )
        st.progress(share, text=f"Освоено {share:.0%}")
        if st.button(
            ":material/school: Учить эту тему",
            key=f"topic-{row['Тема']}",
            width="content",
            help="Выставить фильтр по теме и открыть «Изучение»",
        ):
            # Виджет «Темы» создаётся в сайдбаре раньше страницы, поэтому
            # значение передаём отложенно: app.py применит его до создания.
            st.session_state.pending_topics = [row["Тема"]]
            st.session_state.revealed = False
            candidates = [
                q for q in st.session_state.questions if row["Тема"] in q.topics
            ]
            if candidates:
                st.session_state.question = min(candidates, key=lambda q: q.num).key
            st.switch_page("app_pages/study.py")

st.divider()
if st.button(
    ":material/file_download: Экспорт статичного HTML",
    width="stretch",
    help="Генерирует Python_Developer_Questions.html с подсветкой и поиском",
):
    from reader_quest.html_export import export_html

    output = export_html(
        st.session_state.source_name, base_dir=st.session_state.get("app_dir")
    )
    st.success(f"Файл готов: `{output.name}`", title="Экспорт выполнен")
