"""Автономный HTML-экспорт: тёмная тема One Dark, сайдбар, поиск, прогресс.

Результат — один самодостаточный файл без внешних ресурсов: его можно открыть
в браузере офлайн, отметить выученное (хранится в localStorage) и поискать.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import markdown as md_lib
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import BashLexer, CppLexer, JavaLexer, PythonLexer, TextLexer

from .models import Question
from .parser import parse_questions
from .terms import highlight_html

_CODE_LEXERS: dict[str, type[Lexer]] = {
    "py": PythonLexer,
    "python": PythonLexer,
    "py3": PythonLexer,
    "python3": PythonLexer,
    "bash": BashLexer,
    "sh": BashLexer,
    "shell": BashLexer,
    "console": BashLexer,
    "c++": CppLexer,
    "cpp": CppLexer,
    "java": JavaLexer,
}

# CSS не через f-string: в стилях много фигурных скобок.
_CSS = """
:root {
  --bg: #282c34; --bg-side: #21252b; --bg-card: #2c313a; --bg-code: #1e2127;
  --text: #abb2bf; --text-bright: #e6e6e6; --muted: #7f848e;
  --accent: #61afef; --border: #3e4451;
  --keyword: #c678dd; --type: #61afef; --builtin: #98c379;
  --module: #d19a66; --concept: #e5c07b; --good: #98c379; --bad: #e06c75;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 16px; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.65 system-ui, "Segoe UI", Roboto, sans-serif;
}
.layout { display: flex; min-height: 100vh; }
aside {
  width: 340px; flex: 0 0 340px; background: var(--bg-side);
  border-right: 1px solid var(--border); padding: 18px 14px;
  position: sticky; top: 0; max-height: 100vh; overflow-y: auto;
}
aside h1 { font-size: 17px; color: var(--text-bright); margin: 0 0 4px; }
aside .sub { color: var(--muted); font-size: 12.5px; margin-bottom: 14px; }
#search {
  width: 100%; padding: 9px 12px; border-radius: 8px; font-size: 14px;
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
}
#search:focus { outline: 1px solid var(--accent); }
#toc { list-style: none; margin: 12px 0 0; padding: 0; }
#toc a {
  display: block; padding: 6px 9px; border-radius: 7px; color: var(--text);
  text-decoration: none; font-size: 13.5px; line-height: 1.45;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#toc a:hover { background: var(--bg-card); color: var(--text-bright); }
#toc a.done::after { content: " ✓"; color: var(--good); }
#toc a.review::after { content: " ↻"; color: var(--bad); }
#progress-line { height: 6px; border-radius: 3px; background: var(--border); margin-top: 14px; }
#progress-bar { height: 100%; width: 0; border-radius: 3px; background: var(--good); transition: width .3s; }
#progress-text { font-size: 12.5px; color: var(--muted); margin-top: 6px; }
main { flex: 1; min-width: 0; padding: 26px clamp(14px, 5vw, 60px); max-width: 980px; }
article.qa {
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 4px solid var(--accent); border-radius: 12px;
  padding: 22px 26px 18px; margin-bottom: 26px;
}
article.qa.done { border-left-color: var(--good); }
article.qa.review { border-left-color: var(--bad); }
article.qa h2 { margin: 0 0 4px; font-size: 20px; color: var(--text-bright); }
article.qa .meta { margin-bottom: 14px; }
.badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12px; background: rgba(97,175,239,.14); color: var(--accent);
  margin-right: 6px;
}
.answer { display: none; }
.qa.open .answer { display: block; }
.show-answer {
  padding: 8px 18px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; color: var(--accent); cursor: pointer; font-size: 14px;
}
.show-answer:hover { background: rgba(97,175,239,.12); }
.answer p { margin: 0 0 14px; }
.answer ul, .answer ol { margin: 0 0 14px; padding-left: 26px; }
.answer li { margin-bottom: 7px; }
.answer code {
  background: var(--bg-code); border-radius: 5px; padding: 2px 6px;
  font: 87%/1.5 ui-monospace, "Cascadia Code", Consolas, monospace; color: var(--text-bright);
}
.codehilite {
  background: var(--bg-code); border: 1px solid var(--border);
  border-radius: 9px; padding: 13px 16px; overflow-x: auto; margin: 0 0 14px;
}
.codehilite pre { margin: 0; font: 13.5px/1.6 ui-monospace, "Cascadia Code", Consolas, monospace; }
.term-keyword { color: var(--keyword); font-weight: 600; }
.term-type { color: var(--type); font-weight: 600; }
.term-builtin { color: var(--builtin); font-weight: 600; }
.term-module { color: var(--module); font-weight: 600; }
.term-concept { color: var(--concept); font-weight: 600; }
.mark-row { display: flex; gap: 8px; margin-top: 16px; }
.mark-row button {
  padding: 6px 16px; border-radius: 8px; cursor: pointer; font-size: 13.5px;
  border: 1px solid var(--border); background: transparent; color: var(--text);
}
.mark-row button.on-known { background: rgba(152,195,121,.16); color: var(--good); border-color: var(--good); }
.mark-row button.on-review { background: rgba(224,108,117,.16); color: var(--bad); border-color: var(--bad); }
.no-results { display: none; color: var(--muted); padding: 40px 0; text-align: center; }
#top-btn {
  position: fixed; right: 22px; bottom: 22px; width: 44px; height: 44px;
  border-radius: 50%; border: 1px solid var(--border); background: var(--bg-side);
  color: var(--text); font-size: 20px; cursor: pointer; display: none;
}
#top-btn:hover { color: var(--accent); }
@media (max-width: 900px) {
  .layout { flex-direction: column; }
  aside { position: static; width: auto; flex: none; max-height: none; }
}
@media print {
  aside, #top-btn, .mark-row, .show-answer { display: none; }
  .answer { display: block; }
  body { background: #fff; color: #111; }
}
"""

_JS = """
(function () {
  var KEY = "reader-quest-progress-v1";
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }

  var cards = Array.prototype.slice.call(document.querySelectorAll("article.qa"));
  var tocItems = Array.prototype.slice.call(document.querySelectorAll("#toc a"));

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  function applyToCard(card) {
    var id = card.dataset.id;
    card.classList.toggle("done", state[id] === "known");
    card.classList.toggle("review", state[id] === "review");
    var known = card.querySelector("[data-mark=known]");
    var review = card.querySelector("[data-mark=review]");
    known.classList.toggle("on-known", state[id] === "known");
    review.classList.toggle("on-review", state[id] === "review");
  }

  function refreshProgress() {
    var total = cards.length;
    var known = cards.filter(function (c) { return state[c.dataset.id] === "known"; }).length;
    var review = cards.filter(function (c) { return state[c.dataset.id] === "review"; }).length;
    document.getElementById("progress-bar").style.width = (total ? (100 * known / total) : 0) + "%";
    document.getElementById("progress-text").textContent =
      "Знаю " + known + " из " + total + " · на повторе " + review;
    tocItems.forEach(function (a) {
      var id = a.dataset.id;
      a.classList.toggle("done", state[id] === "known");
      a.classList.toggle("review", state[id] === "review");
    });
  }

  cards.forEach(function (card) {
    var id = card.dataset.id;
    var toggle = card.querySelector(".show-answer");
    if (toggle) {
      toggle.addEventListener("click", function () { card.classList.add("open"); toggle.remove(); });
    }
    card.querySelectorAll("[data-mark]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mark = btn.dataset.mark;
        state[id] = state[id] === mark ? null : mark;
        if (!state[id]) delete state[id];
        save();
        applyToCard(card);
        refreshProgress();
      });
    });
    applyToCard(card);
  });
  refreshProgress();

  var search = document.getElementById("search");
  var counter = document.getElementById("found-count");
  search.addEventListener("input", function () {
    var query = search.value.trim().toLowerCase();
    var words = query.split(/\\s+/).filter(Boolean);
    var visible = 0;
    cards.forEach(function (card) {
      var haystack = (card.dataset.search || "").toLowerCase();
      var show = words.every(function (w) { return haystack.indexOf(w) !== -1; });
      card.style.display = show ? "" : "none";
      if (show) visible += 1;
    });
    tocItems.forEach(function (a) {
      var card = document.getElementById(a.getAttribute("href").slice(1));
      a.parentElement.style.display = card && card.style.display === "none" ? "none" : "";
    });
    counter.textContent = visible + " из " + cards.length;
    document.querySelector(".no-results").style.display = visible ? "none" : "block";
  });

  var topBtn = document.getElementById("top-btn");
  window.addEventListener("scroll", function () {
    topBtn.style.display = window.scrollY > 700 ? "block" : "none";
  });
  topBtn.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
})();
"""

_MD_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def _lexer(language: str) -> Lexer:
    name = (language or "").strip().lower()
    return _CODE_LEXERS.get(name, TextLexer)()  # type: ignore[no-any-return]


def _render_code(block_text: str, language: str) -> str:
    formatter = HtmlFormatter(nowrap=False, classprefix="pg-")
    return f'<div class="codehilite">{pyg_highlight(block_text, _lexer(language), formatter)}</div>'


def _render_prose(text: str) -> str:
    return md_lib.markdown(highlight_html(text), extensions=_MD_EXTENSIONS)


def export_html(
    source: str,
    base_dir: Path | None = None,
    output: Path | None = None,
    questions: Sequence[Question] | None = None,
) -> Path:
    """Генерирует автономный HTML-файл и возвращает путь к нему."""

    base = (base_dir or Path.cwd()).resolve()
    source_path = base / source
    if not source_path.exists():
        raise FileNotFoundError(f"Не найден файл с вопросами: {source_path}")

    if questions is None:
        questions = parse_questions(source_path.read_text(encoding="utf-8"))
    if output is None:
        output = base / "Python_Developer_Questions.html"

    pygments_css = HtmlFormatter(style="one-dark", classprefix="pg-").get_style_defs(
        ".codehilite"  # type: ignore[no-untyped-call]
    )

    cards: list[str] = []
    toc: list[str] = []
    for question in questions:
        anchor = f"q-{question.key}"
        title = html.escape(question.title)
        badges = "".join(
            f'<span class="badge">{html.escape(t)}</span>' for t in question.topics
        )
        search_blob = html.escape(
            f"{question.num} {question.title} {question.body}".lower(), quote=True
        )
        body_parts: list[str] = []
        if question.body:
            for block in question.blocks:
                if block.kind == "code":
                    body_parts.append(_render_code(block.text, block.language))
                else:
                    body_parts.append(_render_prose(block.text))
        else:
            body_parts.append("<p><em>В исходном файле ответа нет.</em></p>")
        cards.append(
            f'<article class="qa" id="{anchor}" data-id="{question.key}" data-search="{search_blob}">\n'
            f"<h2>{question.num}. {title}</h2>\n"
            f'<div class="meta">{badges}</div>\n'
            f'<button class="show-answer" type="button">Показать ответ</button>\n'
            f'<div class="answer">{"".join(body_parts)}</div>\n'
            f'<div class="mark-row">'
            f'<button type="button" data-mark="known">Знаю</button>'
            f'<button type="button" data-mark="review">Повторить</button>'
            f"</div>\n</article>"
        )
        toc.append(
            f'<li><a href="#{anchor}" data-id="{question.key}" title="{title}">'
            f"{question.num}. {title}</a></li>"
        )

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    document = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Python собеседование — {len(questions)} вопросов с ответами</title>
<style>{_CSS}</style>
<style>{pygments_css}</style>
</head>
<body>
<div class="layout">
<aside>
  <h1>🐍 Python собеседование</h1>
  <div class="sub">Источник: {html.escape(source)} · сгенерировано {generated}</div>
  <input id="search" type="search" placeholder="Поиск: GIL, декоратор, isinstance…" autocomplete="off">
  <div id="found-count" class="sub" style="margin-top:6px">{len(questions)} из {len(questions)}</div>
  <div id="progress-line"><div id="progress-bar"></div></div>
  <div id="progress-text">Знаю 0 из {len(questions)} · на повторе 0</div>
  <ul id="toc">{"".join(toc)}</ul>
</aside>
<main>
{"".join(cards)}
<div class="no-results">Ничего не найдено — попробуйте другой запрос.</div>
</main>
</div>
<button id="top-btn" type="button" title="Наверх">↑</button>
<script>{_JS}</script>
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")
    return output


__all__ = ["export_html"]
