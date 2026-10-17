"""Read `MirrorPolicy` files. Nothing about a project, a label or a destination lives in code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

TRACK_LABEL = "admission-track"
# metadata.name names files and directories (journal, reports, work): a Kubernetes DNS-1123
# subdomain, so never a path (`../x`) nor a shell word (`a;b`)
NAME = re.compile(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?")
NAME_MAX = 253


class PolicyError(Exception):
    """A file that is not a readable MirrorPolicy."""


@dataclass(frozen=True)
class Policy:
    name: str
    path: Path
    track: str | None
    document: dict


def load(path: str | Path) -> Policy:
    path = Path(path)
    try:
        doc = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"{path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("kind") != "MirrorPolicy":
        raise PolicyError(f"{path}: not a MirrorPolicy")
    meta = doc.get("metadata") or {}
    if not meta.get("name"):
        raise PolicyError(f"{path}: metadata.name is missing")
    name = meta["name"]
    if not isinstance(name, str) or len(name) > NAME_MAX or not NAME.fullmatch(name):
        raise PolicyError(
            f"{path}: metadata.name {name!r} is not a DNS-1123 subdomain "
            "(lowercase letters, digits, '-' and '.', at most 253 characters)"
        )
    return Policy(meta["name"], path, (meta.get("labels") or {}).get(TRACK_LABEL), doc)


def load_dir(directory: str | Path) -> tuple[list[Policy], list[str]]:
    """Every `*.yaml` under `directory`; unreadable files are reported, never fatal."""
    policies, errors = [], []
    for path in sorted(Path(directory).rglob("*.yaml")):
        try:
            policies.append(load(path))
        except PolicyError as exc:
            errors.append(str(exc))
    return policies, errors
