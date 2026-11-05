"""Страница «Статистика»: прогресс по темам и слабые места."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from reader_quest.app_helpers import empty_state
from reader_quest.html_export import export_html
from reader_quest.models import Progress, Question


@dataclass(frozen=True)
class TopicRow:
    """Одна строка сводки по теме."""

    name: str
    total: int
    known: int
    review: int

    @property
    def uncovered(self) -> int:
        return self.total - self.known

    @property
    def share(self) -> float:
        return self.known / self.total if self.total else 0.0


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
rows = [TopicRow(name=topic, **stats) for topic, stats in topic_stats.items()]
rows.sort(key=lambda row: (-row.uncovered, row.name))

st.caption("Слабые темы сверху: сначала там, где больше вопросов без отметки «знаю».")
for row in rows:
    with st.container(border=True):
        top = st.container(horizontal=True, vertical_alignment="center")
        top.markdown(f"**{row.name}**", width="stretch")
        top.caption(f"{row.known}/{row.total} знаю · повторить: {row.review}")
        st.progress(row.share, text=f"Освоено {row.share:.0%}")
        if st.button(
            ":material/school: Учить эту тему",
            key=f"topic-{row.name}",
            width="content",
            help="Выставить фильтр по теме и открыть «Изучение»",
        ):
            # Виджет «Темы» создаётся в сайдбаре раньше страницы, поэтому
            # значение передаём отложенно: app.py применит его до создания.
            st.session_state.pending_topics = [row.name]
            st.session_state.revealed = False
            candidates = [q for q in questions if row.name in q.topics]
            if candidates:
                st.session_state.question = min(candidates, key=lambda q: q.num).key
            st.switch_page("app_pages/study.py")

st.divider()
if st.button(
    ":material/file_download: Экспорт статичного HTML",
    width="stretch",
    help="Генерирует Python_Developer_Questions.html с подсветкой и поиском",
):
    output = export_html(
        st.session_state.source_name, base_dir=st.session_state.get("app_dir")
    )
    st.success(f"Файл готов: `{output.name}`", title="Экспорт выполнен")
