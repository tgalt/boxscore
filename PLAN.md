# boxscore — Build Plan

> Your repos already keep score. boxscore shows you the game.

**boxscore** turns the markdown checklists you already maintain across your repos into a static
status dashboard: one hub page with a card per project (progress, next open item, freshness),
linking to a rendered page per project. No database, no LLM, no tokens, no server-side code at
view time — a parser, two templates, and a cron.

## Principles

1. **Status is derived, never summarized.** Every number on the dashboard is computed from
   checkbox state in version-controlled markdown. If it's not in a checklist, it's not on the
   board. (No AI narrator — a status without an artifact behind it is a vibe.)
2. **Rot is visible.** Every source file carries a freshness badge from its last git commit
   date. A stale dashboard that looks current is worse than no dashboard.
3. **Honest progress semantics.** Checklists are not commensurate across projects — bars always
   show the real fraction (`14/31`), never a bare percentage implying comparability.
4. **Secrets-free by construction.** The tool reads local git checkouts and writes static
   files. The repo ships code + demo data only; the operator's real registry and all generated
   output are gitignored.
5. **Boring technology.** Python 3.11+ stdlib + PyYAML. No build step, no JS framework,
   hand-written CSS. Vanilla HTML output.

## Architecture

```
projects.yaml (gitignored; .example ships)      ← the only config
        │
        ▼
scan: for each project → read checklist file(s) from its local git checkout
        │   parse GFM checkboxes + headings → sections, items, done/total
        │   git log -1 per file → freshness; git log --since=7d → recently-changed items
        ▼
model: projects[] { name, summary, fraction, next_open_item, freshness, sections[] }
        ▼
render: site/index.html  (hub: cards, bars, next, badges)
        site/p/<slug>.html (per-project: rendered checklist, anchors, evidence links)
        ▼
serve: any static server. Recommended: `tailscale serve` for a private tailnet-only
       HTTPS dashboard; GitHub Pages/anything for public use cases.
```

### Registry format (`projects.yaml`)

```yaml
projects:
  - name: Example App
    slug: example-app
    summary: One-line description shown on the hub card.
    repo: ~/code/example-app          # local checkout; boxscore never clones
    checklists:
      - CHECKLIST.md                  # one or more, repo-relative
      - docs/launch-gates.md
    link: https://github.com/you/example-app   # optional card link
```

### Parsing rules

- Items: GFM task-list syntax `- [ ]` / `- [x]` (and `*` bullets), nested items counted
  individually, parents shown as groups.
- Sections: nearest preceding heading; per-section fractions on project pages.
- **Next:** first unchecked item in file order — the single most useful line on a card.
- Freshness: `git log -1 --format=%cs -- <file>`; badge thresholds: green ≤ 7 d,
  amber ≤ 30 d, red > 30 d.
- Recently changed: items in hunks touched within 7 days (via `git log -p --since`), marked
  with an accent dot — the "changed overnight" panel, computed not narrated.
- Non-checklist markdown between items is preserved on project pages (notes/evidence links
  render as-is).

## Milestones

Each milestone has a proof-of-work; boxscore tracks its own build (this file is the first
registry entry — the dashboard is self-hosting from M1).

### M0 — Parser + model
- [x] `boxscore/parse.py`: checklist file → sections/items/fractions (pure function, no git)
- [x] `boxscore/gitmeta.py`: freshness + recently-changed via subprocess git (no deps)
- [x] `boxscore/registry.py`: load + validate `projects.yaml`, expand `~`, fail loud on
      missing paths
- [x] Unit tests on a fixtures dir (weird nesting, no headings, empty files, non-UTF8 guard)
- [x] **Proof:** parser output for this `PLAN.md` matches a hand count of its boxes

### M1 — Renderer + hub
- [x] `boxscore/render.py`: Jinja-free stdlib templating (f-strings/`string.Template`) or
      vendored minimal templates — zero pip deps beyond PyYAML
- [x] Hub + project page markup, dark theme, no external fonts/CDNs (self-contained CSS;
      privacy by default) — *deviation: inline in `render.py` rather than a `templates/` dir*
- [x] Hub card: name, summary, bar + true fraction, **Next:** line, freshness badge, link
- [x] Project page: per-section fractions, anchors, recently-changed accents
- [x] `boxscore build` CLI entry (`python -m boxscore build -c projects.yaml -o site/`)
- [ ] **Proof:** demo registry (3 fake projects in `examples/`) renders; screenshots in README
      come from the demo, never real data

### M2 — Operate
- [x] `.gitignore`: `projects.yaml`, `site/`, `__pycache__`
- [x] `projects.yaml.example` + `examples/` fixtures
- [x] Cron/systemd-timer snippet in README (rebuild every 30 min; `git -C <repo> pull`
      optional pre-step per project)
- [x] `tailscale serve` recipe in README for private tailnet hosting
- [ ] **Proof:** dashboard serving over tailnet HTTPS *(done — serve proxy to a
      localhost static server; directory-serve needs root, proxy only needs operator)*;
      phone loads it; survives a reboot *(both pending confirmation)*

### M3 — Polish that earns its keep (only after a week of real use)
- [ ] Hub sort options: by staleness (default — rot floats up), by progress, by name
- [x] `boxscore check` CLI: exit non-zero if any source is red-stale (CI-able honesty)
- [x] Per-item permalinks back to the source file's line on GitHub (evidence links)
- [x] Optional JSON output (`site/status.json`) for other tools to consume
- [ ] **Proof:** one week of daily use without hand-editing any generated file

### M4 — Public release gate
- [ ] README: pitch, demo screenshot, quickstart, the four principles
- [ ] MIT license
- [ ] Sweep: no real project names, paths, hostnames, or tailnet names anywhere in repo
      history (plan for this from commit one — history is forever)
- [ ] **Proof:** a stranger can clone, run the demo, and get the demo dashboard in < 5 minutes

## Non-goals (v1)

- No write-back (the dashboard never edits checklists — single-writer stays the human/agent
  in the repo)
- No auth, no accounts, no server-side rendering, no database
- No LLM anywhere in the pipeline (a future *auditor* that verifies checked items against
  tests/endpoints is interesting — it is a separate tool that edits checklists, upstream of
  boxscore, not part of it)
- No remote cloning — boxscore reads checkouts you already have

## Risks / open questions

- [ ] Checklist dialect drift (setext headings, HTML comments, Obsidian syntax) — fixtures
      grow as encountered; parser stays permissive, never crashes the build
- [ ] Giant checklists (hundreds of items) — cap "recently changed" scan cost; render is cheap
- [ ] Per-item git blame for "changed recently" is approximate (hunk-level) — accept; badge
      the file, accent the hunk, don't promise line-level truth
