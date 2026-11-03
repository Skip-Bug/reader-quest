"""Тесты парсера Markdown с вопросами."""

from reader_quest.parser import parse_questions

FIXTURE = """\
# Вопрос-ответ, для Python-разработчика.

<div align="right">
    <b><a href="#">↥ вернуться к началу</a></b>
</div>

## 1. Что такое python?
Python - это язык программирования. Типы: int, str, list.

```py
print("hello")
```

<div align="right">
    <b><a href="#">↥ вернуться к началу</a></b>
</div>

## 2. Что такое GIL?
GIL защищает память.

```py
x = 1
```

## 4. Вопрос с незакрытым кодом
```py
value = 2
## 5. Это заголовок внутри незакрытого блока
    ```python
    >>> -30 % 10
    ```
    Результат ноль.

## 6. Однострочный код
Списковое включение пишется так:
```new_list = [x for x in y]```
и даёт новый список.
"""


def parse() -> list:
    return parse_questions(FIXTURE)


def test_finds_all_questions_including_broken_markup():
    questions = parse()
    assert [q.num for q in questions] == [1, 2, 4, 5, 6]


def test_footers_and_noise_removed():
    questions = parse()
    for question in questions:
        assert "вернуться к началу" not in question.body
        assert "<div" not in question.body


def test_simple_question_blocks():
    first = parse()[0]
    assert first.title == "Что такое python?"
    kinds = [b.kind for b in first.blocks]
    assert kinds == ["prose", "code"]
    assert first.blocks[1].language == "py"
    assert 'print("hello")' in first.blocks[1].text


def test_unbalanced_fence_does_not_swallow_next_question():
    questions = parse()
    fourth = questions[2]
    assert fourth.title == "Вопрос с незакрытым кодом"
    assert [b.kind for b in fourth.blocks] == ["code"]
    assert fourth.blocks[0].text == "value = 2"


def test_indented_fence_is_dedented():
    questions = parse()
    fifth = questions[3]
    assert fifth.blocks[0].kind == "code"
    assert fifth.blocks[0].text == ">>> -30 % 10"
    assert fifth.blocks[1].kind == "prose"
    assert "Результат ноль" in fifth.blocks[1].text


def test_single_line_fence_becomes_code_block():
    questions = parse()
    sixth = questions[4]
    code_blocks = [b for b in sixth.blocks if b.kind == "code"]
    assert len(code_blocks) == 1
    assert code_blocks[0].text == "new_list = [x for x in y]"


def test_keys_are_stable_and_unique():
    questions = parse()
    keys = [q.key for q in questions]
    assert len(keys) == len(set(keys))
    assert keys[0].startswith("1-")


def test_real_source_file_parses_fully():
    """Смоук на реальном файле: количество и отсутствие потерянных фенсов."""

    from pathlib import Path

    source = Path(__file__).parent.parent / "Python_Developer_Questions.md"
    questions = parse_questions(source.read_text(encoding="utf-8"))
    assert len(questions) >= 400
    for question in questions:
        for block in question.blocks:
            if block.kind == "prose":
                assert "```" not in block.text, f"q{question.num}"
