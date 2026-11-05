"""Тесты прогресса, фильтров и тем."""

from reader_quest.filters import filter_questions, normalize_search
from reader_quest.models import Progress, Question
from reader_quest.progress import default_path, load, save
from reader_quest.topics import FALLBACK_TOPIC, classify


def _question(num: int, title: str, key: str | None = None) -> Question:
    return Question(
        key=key or f"{num}-test",
        num=num,
        title=title,
        body=f"Ответ на вопрос {num}",
        topics=classify(title),
    )


def test_progress_roundtrip(tmp_path):
    path = default_path(tmp_path)
    progress = Progress(marks={"1-abc": "known", "2-def": "review", "3-ghi": "bogus"})
    save(path, progress, "source.md")

    loaded = load(path)
    assert loaded.status("1-abc") == "known"
    assert loaded.status("2-def") == "review"
    assert loaded.status("3-ghi") == "new"  # мусорные значения отброшены


def test_progress_survives_broken_file(tmp_path):
    path = default_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert load(path).marks == {}


def test_save_is_atomic(tmp_path):
    path = default_path(tmp_path)
    save(path, Progress(marks={"1-x": "known"}), "s.md")
    leftovers = list(path.parent.glob(".progress-*.tmp"))
    assert leftovers == []


def test_progress_reset():
    """Сброс отметки возвращает вопрос в статус «новый» (используется
    кнопкой «Сбросить отметку» и диалогом полного сброса)."""

    progress = Progress(marks={"a": "known", "b": "review"})
    progress.reset("a")
    assert progress.status("a") == "new"
    assert "a" not in progress.marks
    assert progress.status("b") == "review"
    progress.reset("нет-такого-ключа")  # не падает
    assert progress.counts(["a", "b"]) == {"new": 1, "known": 0, "review": 1}


def test_filter_by_search_and_topics():
    questions = [
        _question(1, "Что такое GIL?", "a"),
        _question(2, "Что такое list?", "b"),
        _question(3, "Расскажите про декораторы", "c"),
    ]
    assert [q.key for q in filter_questions(questions, search="gil")] == ["a"]
    assert [q.key for q in filter_questions(questions, search="что такое")] == ["a", "b"]
    assert [q.key for q in filter_questions(questions, topics=["Декораторы и функции"])] == ["c"]


def test_filter_by_status():
    questions = [_question(1, "GIL", "a"), _question(2, "list", "b")]
    progress = Progress(marks={"a": "review"})
    assert [q.key for q in filter_questions(questions, statuses=["review"], progress=progress)] == ["a"]
    assert [q.key for q in filter_questions(questions, statuses=["new"], progress=progress)] == ["b"]


def test_search_normalization():
    assert normalize_search("  GIL   декоратор ") == ["gil", "декоратор"]


def test_classify_prefers_title_hits():
    assert "Декораторы и функции" in classify("Что такое декоратор?")
    # Тема из заголовка важнее случайного слова в теле.
    topics = classify("Что такое *args?", "Тут упоминается словарь dict")
    assert "Декораторы и функции" in topics
    assert "Коллекции" not in topics


def test_classify_fallback():
    assert classify("Совершенно неопознанный вопрос") == (FALLBACK_TOPIC,)
