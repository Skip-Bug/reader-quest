"""Тесты CLI-точек: ``reader_quest.cli.main`` и ``highlight.main``."""

from pathlib import Path

import pytest

import highlight
from reader_quest import cli

SAMPLE = """# Вопросы

## 1. Что такое GIL?

Ответ про **GIL** и потоки в `threading`.

```python
def work():
    return 1
```

## 2. Что такое список?

Ответ про list.
"""


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    """Мини-проект во временной папке: app.py плюс сборник с тем же именем,
    что и боевой (cli ищет источник рядом с app.py)."""

    (tmp_path / "app.py").write_text("", encoding="utf-8")
    file = tmp_path / cli.DEFAULT_SOURCE
    file.write_text(SAMPLE, encoding="utf-8")
    return file


def test_cli_build_writes_html(
    tmp_path: Path, source: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    del source
    monkeypatch.setattr(cli, "_root", lambda: tmp_path)

    assert cli.main(["build"]) == 0

    html_file = tmp_path / "Python_Developer_Questions.html"
    assert html_file.exists()
    page = html_file.read_text(encoding="utf-8")
    assert "Что такое GIL" in page
    assert "codehilite" in page
    assert "HTML готов" in capsys.readouterr().out


def test_cli_without_app_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Команда run не должна запускать streamlit вне папки проекта."""

    monkeypatch.setattr(cli, "_root", lambda: tmp_path)

    assert cli.main(["run"]) == 1


def test_cli_build_without_source_explains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Без файла с вопросами — понятное сообщение, а не трейсбек: именно этот
    сценарий видит человек, который переименовал или удалил источник."""

    (tmp_path / "app.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_root", lambda: tmp_path)

    assert cli.main(["build"]) == 1
    err = capsys.readouterr().err
    assert "Не найден файл с вопросами" in err
    assert "## 1. Вопрос" in err


def test_highlight_main_builds_html_and_md(
    tmp_path: Path, source: Path, capsys
) -> None:
    assert highlight.main(["--input", str(source), "--md"]) == 0

    assert (tmp_path / highlight.DEFAULT_HTML).exists()
    md_output = tmp_path / highlight.DEFAULT_MD
    assert md_output.exists()
    assert 'class="term-concept"' in md_output.read_text(encoding="utf-8")
    assert "Прочитано вопросов: 2" in capsys.readouterr().out


def test_highlight_main_without_md_only_html(tmp_path: Path, source: Path) -> None:
    assert highlight.main(["--input", str(source)]) == 0

    assert (tmp_path / highlight.DEFAULT_HTML).exists()
    assert not (tmp_path / highlight.DEFAULT_MD).exists()


def test_highlight_main_missing_input(tmp_path: Path, capsys) -> None:
    assert highlight.main(["--input", str(tmp_path / "нет-такого.md")]) == 1
    assert "Не найден исходный файл" in capsys.readouterr().err
