"""Тесты поиска и дедупликации файлов с вопросами."""

from pathlib import Path

from reader_quest.sources import GENERATED_MD, discover_and_parse

BASE = """\
## 1. Что такое python?
Python - язык программирования.

## 2. Что такое GIL?
Глобальная блокировка интерпретатора.
"""

# Тот же сборник с рекламным подвалом после каждого ответа.
WITH_FOOTER = BASE.replace(
    "Глобальная блокировка интерпретатора.\n",
    "Глобальная блокировка интерпретатора.\n\n"
    '<div align="right">\n'
    '    <b><a href="#">↥ вернуться к началу</a></b><br>\n'
    '    <b><a href="#">если вам понравилось поставьте пожалуйста ★ </a></b>\n'
    "</div>\n",
)

SMALL = "## 1. Единственный вопрос?\nОтвет.\n"


def _write(tmp_path: Path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text, encoding="utf-8")


def test_finds_files_with_enough_questions(tmp_path):
    _write(tmp_path, "Python_Developer_Questions.md", BASE)
    _write(tmp_path, "мелочь.md", SMALL)

    result = discover_and_parse(tmp_path, min_questions=2)
    assert list(result) == ["Python_Developer_Questions.md"]
    assert len(result["Python_Developer_Questions.md"]) == 2


def test_duplicate_content_is_shown_once(tmp_path):
    _write(tmp_path, "Python_Developer_Questions.md", BASE)
    _write(tmp_path, "400 вопросов с ответами.md", WITH_FOOTER)

    result = discover_and_parse(tmp_path, min_questions=2)
    # Рекламный подвал парсер вырезает, поэтому содержимое идентично:
    # остаётся один источник с более коротким именем.
    assert list(result) == ["Python_Developer_Questions.md"]
    assert len(result["Python_Developer_Questions.md"]) == 2


def test_generated_highlighted_is_excluded(tmp_path):
    _write(tmp_path, "Python_Developer_Questions.md", BASE)
    _write(tmp_path, GENERATED_MD, BASE + "\nлишнее")

    result = discover_and_parse(tmp_path, min_questions=2)
    assert list(result) == ["Python_Developer_Questions.md"]


def test_more_questions_win_priority(tmp_path):
    _write(tmp_path, "старый.md", BASE)
    _write(
        tmp_path,
        "полный.md",
        BASE + "\n## 3. Что такое декоратор?\nФункция-обёртка.\n",
    )

    result = discover_and_parse(tmp_path, min_questions=2)
    # Содержимое разное — это не дубликаты: остаются оба, больший первым.
    assert list(result) == ["полный.md", "старый.md"]
    assert len(result["полный.md"]) == 3


def test_missing_directory_is_safe(tmp_path):
    assert discover_and_parse(tmp_path / "нет-такой") == {}


def test_real_project_dir_single_source():
    """На живой папке проекта дубликат «400 вопросов…» схлопывается."""

    project = Path(__file__).parent.parent
    result = discover_and_parse(project)
    assert list(result) == ["Python_Developer_Questions.md"]
    assert len(result["Python_Developer_Questions.md"]) >= 400
