"""Модели данных приложения."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["new", "known", "review"]


@dataclass(frozen=True)
class Block:
    """Кусок ответа: либо обычный markdown-текст, либо блок кода."""

    kind: Literal["prose", "code"]
    text: str
    language: str = ""


@dataclass(frozen=True)
class Question:
    """Один вопрос с ответом."""

    key: str
    num: int
    title: str
    body: str
    blocks: tuple[Block, ...] = ()
    topics: tuple[str, ...] = ()

    @property
    def has_code(self) -> bool:
        return any(b.kind == "code" for b in self.blocks)

    @property
    def words(self) -> int:
        return len(self.body.split())


@dataclass
class Progress:
    """Отметки пользователя о знании вопросов, ключ — Question.key."""

    marks: dict[str, str] = field(default_factory=dict)

    def status(self, key: str) -> Status:
        value = self.marks.get(key)
        return value if value in ("known", "review") else "new"

    def counts(self, keys: list[str] | None = None) -> dict[str, int]:
        result = {"new": 0, "known": 0, "review": 0}
        for key in keys or self.marks:
            result[self.status(key)] += 1
        return result
