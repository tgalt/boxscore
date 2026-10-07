"""Checklist markdown -> structured model. Pure functions, no git, no I/O."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CHECK_RE = re.compile(r"^(\s*)[-*]\s+\[([ xX])\]\s+(.*)$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Item:
    text: str
    done: bool
    line: int  # 1-based line number in the source file
    indent: int


@dataclass
class Section:
    title: str
    level: int
    items: list[Item] = field(default_factory=list)

    @property
    def done(self) -> int:
        return sum(1 for i in self.items if i.done)

    @property
    def total(self) -> int:
        return len(self.items)


@dataclass
class Checklist:
    sections: list[Section]

    @property
    def done(self) -> int:
        return sum(s.done for s in self.sections)

    @property
    def total(self) -> int:
        return sum(s.total for s in self.sections)

    @property
    def first_open(self) -> Item | None:
        for s in self.sections:
            for i in s.items:
                if not i.done:
                    return i
        return None


def parse_checklist(text: str) -> Checklist:
    """Parse GFM task-list items grouped under their nearest preceding heading.

    Content inside fenced code blocks is ignored. Files with no headings get a
    single unnamed section. Never raises on weird input — worst case: no items.
    """
    sections: list[Section] = []
    current = Section(title="", level=0)
    in_fence = False
    fence_marker = ""

    for lineno, raw in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence = False
            continue
        if in_fence:
            continue

        head = HEAD_RE.match(raw)
        if head:
            if current.items or (current.title and sections is not None):
                sections.append(current)
            current = Section(title=head.group(2), level=len(head.group(1)))
            continue

        check = CHECK_RE.match(raw)
        if check:
            indent, mark, body = check.groups()
            current.items.append(
                Item(text=body.strip(), done=mark in "xX",
                     line=lineno, indent=len(indent))
            )

    sections.append(current)
    # keep sections that carry items; preserve order
    kept = [s for s in sections if s.items]
    return Checklist(sections=kept)
