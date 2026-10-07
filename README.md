# boxscore

> Your repos already keep score. boxscore shows you the game.

Turns the markdown checklists you already maintain (`- [ ]` / `- [x]`) across your repos into a
static status dashboard: a hub page with a card per project — true-fraction progress bar, the
next open item, and a freshness badge per source file — linking to a rendered page per project.

No database. No LLM. No tokens. Status is **derived from checkbox state in version-controlled
markdown**, never summarized by anything that can hallucinate. Stale sources are badged, because
a dashboard that looks current and isn't is worse than none.

## Quickstart (demo)

```bash
git clone https://github.com/tgalt/boxscore && cd boxscore
python3 -m boxscore build -c examples/demo.yaml -o site/
python3 -m http.server -d site 8000   # open http://localhost:8000
```

Requires Python 3.11+ and PyYAML. Then copy `projects.yaml.example` to `projects.yaml`
(gitignored) and point it at your own checkouts. Full design + roadmap: [PLAN.md](PLAN.md).

Private hosting tip: serve `site/` over your tailnet with `tailscale serve`.
