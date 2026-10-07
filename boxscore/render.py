"""Render the model to a static site: one hub page + one page per project.

Self-contained output: inline CSS, no external fonts, no CDNs, no JS.
"""
from __future__ import annotations

import datetime
import html
import os
import re
from dataclasses import dataclass, field

from . import gitmeta
from .parse import Checklist, parse_checklist
from .registry import Project

BADGE_LABEL = {"green": "fresh", "amber": "aging", "red": "stale", "unknown": "no history"}

CSS = """
:root { --bg:#0d0f13; --card:#14171e; --text:#e8eaf0; --muted:#8b95a9;
        --border:#1e2230; --accent:#7cc9ff; --green:#4bb58a; --amber:#d9a441;
        --red:#d96c6c; --bar-bg:#1e2230; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
       font:15px/1.55 system-ui, sans-serif; }
header { border-bottom:1px solid var(--border); padding:1rem 1.25rem;
         display:flex; align-items:baseline; gap:0.75rem; }
h1 { font-size:1.05rem; margin:0; color:var(--accent); }
h1 a { color:inherit; text-decoration:none; }
.sub { color:var(--muted); font-size:0.8rem; }
main { max-width:980px; margin:0 auto; padding:1.5rem 1.25rem 4rem; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:1rem; }
.card { background:var(--card); border:1px solid var(--border); border-radius:10px;
        padding:1rem 1.1rem; }
.card h2 { font-size:1rem; margin:0 0 0.2rem; }
.card h2 a { color:var(--text); text-decoration:none; }
.card h2 a:hover { color:var(--accent); }
.summary { color:var(--muted); font-size:0.85rem; margin:0 0 0.75rem; min-height:2.4em; }
.bar { background:var(--bar-bg); border-radius:5px; height:8px; overflow:hidden; }
.bar > div { background:var(--green); height:100%; }
.frac { font-variant-numeric:tabular-nums; font-size:0.8rem; color:var(--muted);
        margin:0.3rem 0 0.6rem; display:flex; justify-content:space-between; }
.next { font-size:0.85rem; margin:0.4rem 0 0.6rem; }
.next b { color:var(--accent); font-weight:600; }
.badges { display:flex; gap:0.4rem; flex-wrap:wrap; }
.badge { font-size:0.7rem; padding:0.1rem 0.5rem; border-radius:999px;
         border:1px solid var(--border); color:var(--muted); }
.badge.green { color:var(--green); border-color:var(--green); }
.badge.amber { color:var(--amber); border-color:var(--amber); }
.badge.red   { color:var(--red);   border-color:var(--red); }
.badge.unknown { color:var(--muted); }
section.src { margin:1.6rem 0; }
section.src > h2 { font-size:0.95rem; color:var(--accent); margin:0 0 0.2rem; }
section.src > .meta { color:var(--muted); font-size:0.78rem; margin-bottom:0.6rem; }
h3.sec { font-size:0.9rem; margin:1rem 0 0.3rem; }
h3.sec .mini { color:var(--muted); font-weight:400; font-size:0.78rem; }
ul.items { list-style:none; margin:0; padding:0 0 0 0.25rem; }
ul.items li { padding:0.14rem 0; font-size:0.9rem; }
li.done { color:var(--muted); }
li.done .box { color:var(--green); }
li .box { display:inline-block; width:1.3em; }
li.changed::marker { content:""; }
.dot { color:var(--accent); font-size:0.8em; margin-left:0.35em; }
li code { background:var(--bar-bg); padding:0 0.3em; border-radius:4px; font-size:0.85em; }
a.back { color:var(--accent); text-decoration:none; font-size:0.85rem; }
.warn { color:var(--amber); font-size:0.8rem; }
footer { color:var(--muted); font-size:0.75rem; text-align:center; padding:2rem 0; }
"""


@dataclass
class SourceStatus:
    relpath: str
    checklist: Checklist
    fresh: str                    # green/amber/red/unknown
    last_date: str                # ISO or ""
    changed: set[int] = field(default_factory=set)


@dataclass
class ProjectStatus:
    project: Project
    sources: list[SourceStatus]

    @property
    def done(self) -> int:
        return sum(s.checklist.done for s in self.sources)

    @property
    def total(self) -> int:
        return sum(s.checklist.total for s in self.sources)

    @property
    def next_item(self) -> str:
        for s in self.sources:
            item = s.checklist.first_open
            if item:
                return item.text
        return ""

    @property
    def worst_fresh(self) -> str:
        order = ["red", "unknown", "amber", "green"]
        states = [s.fresh for s in self.sources] or ["unknown"]
        for state in order:
            if state in states:
                return state
        return "unknown"


def collect(projects: list[Project]) -> list[ProjectStatus]:
    out = []
    for p in projects:
        sources = []
        for rel in p.checklists:
            path = os.path.join(p.repo, rel)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                checklist = parse_checklist(fh.read())
            date = gitmeta.last_commit_date(p.repo, rel)
            sources.append(SourceStatus(
                relpath=rel,
                checklist=checklist,
                fresh=gitmeta.freshness(date),
                last_date=date.isoformat() if date else "",
                changed=gitmeta.changed_lines(p.repo, rel),
            ))
        out.append(ProjectStatus(project=p, sources=sources))
    return out


def _inline_md(text: str) -> str:
    """Escape, then re-introduce a safe subset: links, bold, code."""
    s = html.escape(text)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _page(title: str, body: str, generated: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{CSS}</style></head>
<body>
<header><h1><a href="/">boxscore</a></h1><span class="sub">{html.escape(title)}</span></header>
<main>{body}</main>
<footer>generated {generated} · boxscore</footer>
</body></html>"""


def _card(ps: ProjectStatus) -> str:
    p, total = ps.project, ps.total
    pct = int(100 * ps.done / total) if total else 0
    next_html = (f'<p class="next"><b>Next:</b> {_inline_md(ps.next_item)}</p>'
                 if ps.next_item else '<p class="next">All items checked.</p>')
    badges = "".join(
        f'<span class="badge {s.fresh}">{html.escape(os.path.basename(s.relpath))}'
        f' · {BADGE_LABEL[s.fresh]}{" " + s.last_date if s.last_date else ""}</span>'
        for s in ps.sources
    )
    missing = (f'<p class="warn">missing: {html.escape(", ".join(p.missing))}</p>'
               if p.missing else "")
    return f"""<div class="card">
<h2><a href="p/{p.slug}.html">{html.escape(p.name)}</a></h2>
<p class="summary">{html.escape(p.summary)}</p>
<div class="bar"><div style="width:{pct}%"></div></div>
<p class="frac"><span>{ps.done}/{total} done</span><span>{pct}%</span></p>
{next_html}
<div class="badges">{badges}</div>
{missing}
</div>"""


def _project_page(ps: ProjectStatus) -> str:
    p = ps.project
    parts = [f'<a class="back" href="/">&larr; all projects</a>',
             f"<h2>{html.escape(p.name)} &mdash; {ps.done}/{ps.total}</h2>"]
    if p.link:
        parts.append(f'<p><a href="{html.escape(p.link)}">{html.escape(p.link)}</a></p>')
    for s in ps.sources:
        parts.append(f'<section class="src"><h2>{html.escape(s.relpath)}</h2>'
                     f'<p class="meta">last change {s.last_date or "unknown"} · '
                     f'{BADGE_LABEL[s.fresh]}</p>')
        for sec in s.checklist.sections:
            title = html.escape(sec.title) if sec.title else "(top)"
            parts.append(f'<h3 class="sec">{title} '
                         f'<span class="mini">{sec.done}/{sec.total}</span></h3>')
            rows = []
            for item in sec.items:
                cls = "done" if item.done else "open"
                box = "&#10003;" if item.done else "&#9744;"
                dot = ('<span class="dot" title="changed in last 7 days">&#9679;</span>'
                       if item.line in s.changed else "")
                pad = ' style="margin-left:1.2em"' if item.indent >= 2 else ""
                rows.append(f'<li class="{cls}"{pad}><span class="box">{box}</span>'
                            f"{_inline_md(item.text)}{dot}</li>")
            parts.append('<ul class="items">' + "\n".join(rows) + "</ul>")
        parts.append("</section>")
    return "\n".join(parts)


def build_site(statuses: list[ProjectStatus], outdir: str) -> None:
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs(os.path.join(outdir, "p"), exist_ok=True)

    # hub: stalest first, then least-done — rot floats up
    order = {"red": 0, "unknown": 1, "amber": 2, "green": 3}
    ranked = sorted(statuses, key=lambda ps: (order[ps.worst_fresh],
                                              ps.done / ps.total if ps.total else 1))
    cards = "\n".join(_card(ps) for ps in ranked)
    hub = _page("projects", f'<div class="grid">{cards}</div>', generated)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(hub)

    for ps in statuses:
        page = _page(ps.project.name, _project_page(ps), generated)
        with open(os.path.join(outdir, "p", f"{ps.project.slug}.html"),
                  "w", encoding="utf-8") as fh:
            fh.write(page)
