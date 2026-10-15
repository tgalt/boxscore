"""Load and validate the projects registry (projects.toml). Fail loud, fail early."""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field


@dataclass
class Project:
    name: str
    slug: str
    summary: str
    repo: str                      # absolute path to a local git checkout
    checklists: list[str]          # repo-relative paths
    link: str = ""
    missing: list[str] = field(default_factory=list)  # checklists not found on disk


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"


def load_registry(path: str) -> list[Project]:
    if path.endswith((".yaml", ".yml")):
        raise SystemExit(f"{path}: YAML registries are no longer supported; "
                         "convert it to TOML (see projects.toml.example)")
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"{path}: registry not found")
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"{path}: invalid TOML: {e}")

    entries = data.get("projects")
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"{path}: expected one or more [[projects]] tables")

    projects: list[Project] = []
    seen_slugs: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or "name" not in entry or "repo" not in entry:
            raise SystemExit(f"{path}: projects[{i}] needs at least 'name' and 'repo'")
        repo = os.path.abspath(os.path.expanduser(str(entry["repo"])))
        if not os.path.isdir(repo):
            raise SystemExit(f"{path}: projects[{i}] repo not found: {repo}")
        checklists = entry.get("checklists") or ["CHECKLIST.md"]
        if not isinstance(checklists, list):
            raise SystemExit(f"{path}: projects[{i}] 'checklists' must be a list")

        slug = str(entry.get("slug") or _slugify(str(entry["name"])))
        if slug in seen_slugs:
            raise SystemExit(f"{path}: duplicate slug '{slug}'")
        seen_slugs.add(slug)

        missing = [c for c in checklists
                   if not os.path.isfile(os.path.join(repo, c))]

        projects.append(Project(
            name=str(entry["name"]),
            slug=slug,
            summary=str(entry.get("summary", "")),
            repo=repo,
            checklists=[str(c) for c in checklists],
            link=str(entry.get("link", "")),
            missing=missing,
        ))
    return projects
