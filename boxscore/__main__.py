"""boxscore CLI: build the static dashboard, or check source freshness.

  python -m boxscore build -c projects.toml -o site/
  python -m boxscore check -c projects.toml          # exit 2 if any source is stale
"""
from __future__ import annotations

import argparse
import sys

from .registry import load_registry
from .render import build_site, collect


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="boxscore")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="generate the static site")
    b.add_argument("-c", "--config", default="projects.toml")
    b.add_argument("-o", "--out", default="site")

    c = sub.add_parser("check", help="exit non-zero if any source is red-stale")
    c.add_argument("-c", "--config", default="projects.toml")

    args = ap.parse_args(argv)
    statuses = collect(load_registry(args.config))

    if args.cmd == "build":
        build_site(statuses, args.out)
        for ps in statuses:
            print(f"{ps.project.slug}: {ps.done}/{ps.total} "
                  f"({ps.worst_fresh})" + (" MISSING:" + ",".join(ps.project.missing)
                                           if ps.project.missing else ""))
        print(f"site written to {args.out}/")
        return 0

    stale = [ps.project.slug for ps in statuses if ps.worst_fresh in ("red", "unknown")]
    if stale:
        print("stale sources in: " + ", ".join(stale))
        return 2
    print("all sources fresh enough")
    return 0


if __name__ == "__main__":
    sys.exit(main())
