"""Автоматическая рубрикация вопросов по темам.

В исходном файле категорий нет, поэтому темы определяются по ключевым словам.
Правила упорядочены: чем выше правило, тем специфичнее тема.
"""

from __future__ import annotations

import re
from typing import Final

TOPIC_RULES: Final[list[tuple[str, str]]] = [
    ("Асинхронность", r"\basyncio\b|async def|await|корутина|event loop|событийн"),
    (
        "Многопоточность и GIL",
        r"\bgil\b|многопоточн|потоки|threading|multiprocess|параллельн|процессор",
    ),
    (
        "Базы данных",
        r"\bsql\b|sqlalchemy|sqlite|база данных|\borm\b|django orm|транзакц|nosql|redis",
    ),
    (
        "Веб и фреймворки",
        r"\bdjango\b|\bflask\b|\bfastapi\b|\bcelery\b|rest api|\bwsgi\b|\basgi\b|микрофреймворк|\bapi\b",
    ),
    (
        "Тестирование и отладка",
        r"тест|unittest|pytest|\bmock\b|отладк|\bpdb\b|профилировк|coverage|логирован",
    ),
    (
        "Исключения и ошибки",
        r"исключен|exception|traceback|\braise\b|\btry\b|ошибк|stack trace",
    ),
    (
        "Генераторы и итерации",
        r"генератор|итератор|\byield\b|comprehension|\biter\(|next\(|цикл for",
    ),
    (
        "Декораторы и функции",
        r"декоратор|lambda|лямбда|kwargs|\*args|замыкани|callable|рекурси|аргумент",
    ),
    (
        "ООП и классы",
        r"\bооп\b|\bclass\b|наследован|инкапсуляц|полиморфизм|абстрактн|магическ|dunder|\bself\b|\bmethod\b|конструктор|dataclass|\bmixin\b",
    ),
    (
        "Типы данных",
        r"\bint\b|\bstr\b|\bfloat\b|\bbool\b|complex|\bbytes\b|типизац|аннотаци|\btyping\b|f-?string|\bdict\b|\btuple\b|\bset\b|\blist\b|строка",
    ),
    (
        "Коллекции",
        r"collections|\bdeque\b|counter|defaultdict|namedtuple|\bheapq\b|словарь|множеств|список|кортеж",
    ),
    (
        "Память",
        r"память|сборщик мусора|\bgc\b|ссылк|утечк|\bheap\b|\bdel\b|deepcopy|копирован|остров",
    ),
    (
        "Файлы и сериализация",
        r"open\(|файл|\bjson\b|pickle|\bcsv\b|\byaml\b|сериализ|encoding|кодировк|utf-?8",
    ),
    (
        "Модули и окружение",
        r"модул|пакет|\bimport\b|\bvenv\b|virtualenv|\bpip\b|setup\.py|poetry|\bwheel\b|__name__|__init__|requirements",
    ),
    (
        "Стандартная библиотека",
        r"itertools|functools|datetime|\bos\.|\bsys\.|стандартн|библиотек|\bre\b",
    ),
    (
        "Алгоритмы и структуры",
        r"алгоритм|big o|сортировк|поиск|бинарн|структур данных|\bстек\b|очередь|дерев|граф|хеш",
    ),
    (
        "Синтаксис и основы",
        r"синтакси|\bpass\b|оператор|переменн|область видимост|globals|locals|\bprint\b|интерпретатор|версии python|pep 8",
    ),
]

_COMPILED: Final[list[tuple[str, re.Pattern[str]]]] = [
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in TOPIC_RULES
]

FALLBACK_TOPIC: Final[str] = "Разное"


def classify(title: str, body: str = "") -> tuple[str, ...]:
    """Возвращает до двух тем.

    Сначала ищем совпадения в заголовке — он короткий и точный. Совпадения в
    тексте ответа учитываются только если заголовок ничего не дал: иначе
    случайное упоминание «словарь» превращает вопрос про ``*args`` в «Коллекции».
    """

    title_hits: list[tuple[str, int]] = []
    body_hits: list[tuple[str, int]] = []
    for position, (name, pattern) in enumerate(_COMPILED):
        if pattern.search(title):
            title_hits.append((name, position))
        elif pattern.search(body):
            body_hits.append((name, position))

    hits = title_hits or body_hits
    if not hits:
        return (FALLBACK_TOPIC,)
    return tuple(name for name, _ in hits[:2])


ALL_TOPICS: Final[tuple[str, ...]] = tuple(name for name, _ in TOPIC_RULES) + (
    FALLBACK_TOPIC,
)
