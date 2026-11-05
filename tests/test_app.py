"""Интеграционные тесты Streamlit-приложения (AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent.parent
APP = ROOT / "app.py"


@pytest.fixture()
def app(tmp_path) -> AppTest:
    """Запускает приложение с прогрессом во временном файле."""

    at = AppTest.from_file(str(APP), default_timeout=90)
    at.session_state["progress_path"] = tmp_path / "progress.json"
    at.run()
    assert not at.exception
    return at


def test_app_renders_without_errors(app: AppTest):
    source = app.selectbox(key="source").value
    # Дубликаты («400 вопросов…» — тот же сборник с рекламным подвалом)
    # дедуплицируются: остаётся один каноничный источник.
    assert source == "Python_Developer_Questions.md"


def test_sidebar_has_filters(app: AppTest):
    assert app.text_input(key="search") is not None
    assert app.multiselect(key="topics") is not None
    assert app.pills(key="statuses") is not None
    assert app.toggle(key="only_code") is not None


def test_default_page_is_study(app: AppTest):
    labels = " ".join(subheader.value for subheader in app.subheader)
    assert "1." in labels  # первый вопрос показан


def _picker(app: AppTest):
    """Виджет выбора вопроса: отсутствует, когда фильтры ничего не вернули."""

    try:
        return app.selectbox(key="question_picker")
    except KeyError:
        return None


def test_search_filters_question_list(app: AppTest):
    app.text_input(key="search").set_value("GIL").run()
    assert not app.exception
    picker = _picker(app)
    assert picker is not None and len(picker.options) >= 1

    app.text_input(key="search").set_value("абракадабра-нет-такого-слова").run()
    assert not app.exception
    assert _picker(app) is None


def test_reveal_answer_and_mark_known(app: AppTest):
    question_key = _picker(app).value

    reveal = [b for b in app.button if "Показать ответ" in (b.label or "")]
    assert reveal, "Кнопка «Показать ответ» должна быть на странице изучения"
    reveal[0].click().run()
    assert not app.exception

    known = [b for b in app.button if "Знал" in (b.label or "")]
    assert known, "Кнопка «Знал» должна появиться вместе с ответом"
    known[0].click().run()
    assert not app.exception
    assert app.session_state["progress"].marks.get(question_key) == "known"


def test_navigation_moves_to_next_question(app: AppTest):
    before = _picker(app).value
    forward = [b for b in app.button if "Вперёд" in (b.label or "")]
    assert forward
    forward[0].click().run()
    assert not app.exception
    after = _picker(app).value
    assert after != before


def test_exam_flow(app: AppTest):
    app.switch_page("app_pages/exam.py").run()
    assert not app.exception

    start = [b for b in app.button if "Начать экзамен" in (b.label or "")]
    assert start
    start[0].click().run()
    assert not app.exception
    assert app.session_state["exam"]["queue"], "Очередь экзамена должна заполниться"

    reveal = [b for b in app.button if "Показать ответ" in (b.label or "")]
    assert reveal
    reveal[0].click().run()
    assert not app.exception


def test_stats_page_shows_topics(app: AppTest):
    app.switch_page("app_pages/stats.py").run()
    assert not app.exception
    metrics = [metric.value for metric in app.metric]
    assert metrics and int(metrics[0]) >= 400


def test_pending_topics_applied_before_widget_creation(app: AppTest):
    """Регрессия: «Учить эту тему» раньше падала с
    StreamlitWidgetAlreadyInstantiatedError, потому что pending_topics
    применялся после создания виджета «Темы»."""

    app.session_state["pending_topics"] = ["Память"]
    app.run()
    assert not app.exception
    topics = app.multiselect(key="topics")
    assert topics is not None and topics.value == ["Память"]


def test_no_query_param_bindings(app: AppTest):
    """Договорённость: не использовать bind="query-params".

    st.switch_page() очищает query-параметры и падает со
    StreamlitAPIException на значениях, связанных с виджетами. Баг
    воспроизводится только в реальном браузере, поэтому фиксируем
    запрет текстом.
    """

    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    code_only = "\n".join(
        line for line in app_source.splitlines() if not line.lstrip().startswith("#")
    )
    assert 'bind="query-params"' not in code_only


def test_reset_requires_dialog_confirmation(app: AppTest):
    """Опасная операция: клик «Сбросить отметки» не удаляет отметки сразу,
    а открывает диалог подтверждения.

    Сам клик внутри диалога AppTest не эмулирует (диалог — fragment,
    полный run() его не открывает повторно), поэтому фактический сброс
    покрыт юнит-тестом Progress.reset.
    """

    reveal = [b for b in app.button if "Показать ответ" in (b.label or "")]
    reveal[0].click().run()
    known = [b for b in app.button if "Знал" in (b.label or "")]
    known[0].click().run()
    assert app.session_state["progress"].marks, "отметка должна появиться"

    reset = [b for b in app.button if "Сбросить отметки" in (b.label or "")]
    assert reset
    reset[0].click().run()
    assert not app.exception
    confirm = [b for b in app.button if "Да, сбросить" in (b.label or "")]
    assert confirm, "должен открыться диалог подтверждения"
    assert app.session_state["progress"].marks, "до подтверждения отметки целые"


def test_nav_buttons_disabled_at_bounds(app: AppTest):
    """Границы выборки: на первом вопросе «Назад» недоступен (без зацикливания)."""

    keys = [q.key for q in app.session_state["visible"]]
    assert app.session_state["question"] == keys[0]
    back = next(b for b in app.button if "Назад" in (b.label or ""))
    assert back.disabled
    forward = next(b for b in app.button if "Вперёд" in (b.label or ""))
    assert not forward.disabled


def test_teach_topic_button_from_stats(app: AppTest):
    app.switch_page("app_pages/stats.py").run()
    teach = [b for b in app.button if "Учить эту тему" in (b.label or "")]
    assert teach
    teach[0].click().run()
    assert not app.exception
    # В рантайме за кликом следует перезапуск app.py: pending_topics должен
    # примениться до создания виджета и не уронить прогон.
    app.run()
    assert not app.exception
