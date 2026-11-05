"""Тесты подсветки терминов."""

from reader_quest.terms import highlight_html, highlight_markdown


def test_keywords_get_violet_directive():
    assert highlight_markdown("Оператор def создаёт функцию") == (
        "Оператор :violet[def] создаёт функцию"
    )


def test_types_get_blue_directive():
    text = highlight_markdown("Типы int и str неизменяемы")
    assert ":blue[int]" in text
    assert ":blue[str]" in text


def test_builtins_get_green_directive():
    # Вызов len() оборачивается в инлайн-код — это тоже ожидаемое поведение.
    assert ":green[len]" in highlight_markdown("Метод len считает элементы")
    assert "`len()`" in highlight_markdown("Функция len() возвращает длину")


def test_concepts_get_yellow_directive():
    assert ":yellow[декоратор]" in highlight_markdown(
        "Мой декоратор оборачивает функцию"
    )
    assert ":yellow[Декоратор]" in highlight_markdown("Декоратор оборачивает функцию")


def test_case_sensitive_abbreviations():
    assert ":yellow[GIL]" in highlight_markdown("Про GIL знает каждый")
    assert ":yellow[gil]" not in highlight_markdown("Слово gil не подсвечивается")


def test_inline_code_and_links_are_untouched():
    text = "Смотрите `list` и [документацию](https://docs.python.org)."
    result = highlight_markdown(text)
    assert "`list`" in result
    assert "[документацию](https://docs.python.org)" in result


def test_star_args_and_dunder_become_inline_code():
    assert "`*args`" in highlight_markdown("Передайте *args в функцию")
    assert "`**kwargs`" in highlight_markdown("А ещё **kwargs")
    assert "`__dict__`" in highlight_markdown("Атрибут __dict__ объекта")


def test_bold_markup_is_not_mangled_into_code():
    """Регрессия: `**GIL**` распадалось как «звёзды + идентификатор», и
    жирный markdown превращался в `` `**GIL`** ``."""

    assert highlight_markdown("Про **GIL** все слышали") == (
        "Про **:yellow[GIL]** все слышали"
    )
    assert highlight_markdown("**важный** абзац") == "**важный** абзац"
    assert "`" not in highlight_markdown("Текст со *курсивом* внутри")


def test_html_version_uses_css_classes():
    result = highlight_html("Ключевое слово class и тип dict")
    assert '<span class="term-keyword">class</span>' in result
    assert '<span class="term-type">dict</span>' in result


def test_empty_text_passes_through():
    assert highlight_markdown("") == ""
    assert highlight_html("") == ""
