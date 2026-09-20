"""Count the bypass instead of estimating it (objective 2, KR2).

Three steps, in this order, because the order is what makes it cheap:

1. **Enumerate** the fleet through Harbor's API. Digests come back from the registry's own
   index; no image is pulled, which is what separates this from `knock audit` on the whole
   fleet (46-115 h, specification gap 22).
2. **Subtract** what came through the door: knock's stamp (`io.knock.policy`, the same
   predicate knock's own coverage uses), then the repositories the existing chain owns
   (D-26, IF-08). What is left is suspect.
3. **Ask the usage oracle** about the suspects *only*. The oracle is the command the house
   already runs for its retention (`KNOCK_USAGE_ORACLE_CMD`, specification 7.3): JSON in,
   `{"last_seen": <ISO|null>}` out. Filtering before asking keeps the call volume on the
   suspect set rather than the whole fleet.

The numerator is the bypass **in service**, not the bypass *stored*: an image nobody runs
costs nobody anything.

**The oracle fails the other way round here.** For `knock purge`, no answer means "protect"
— silence is treated as use. A census must not do that: silence treated as "not in service"
would quietly shrink the number this exists to report. Unanswered suspects are counted
apart, as `unknown`, and the report carries them as the bound on its own result.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

# knock's definitive provenance signal, read exactly as knock's own coverage predicate reads it
# (knock/domain/coverage.py, `is_stamped`): the namespaced lineage key under the default prefix.
STAMP_KEY = "io.knock.policy"
PAGE_SIZE = 100
HOUSE_IDLE_DAYS = 15  # the window the existing retention uses (specification 7.3)


class CensusError(Exception):
    """A technical failure: Harbor or the oracle unusable, or an unreadable answer."""


# --- enumerate ------------------------------------------------------------------------------


class Harbor:
    """Harbor's v2.0 API, read-only and paginated. No image is ever pulled."""

    def __init__(self, url: str, user: str, password: str):
        self.api = url.rstrip("/") + "/api/v2.0"
        self._auth = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        self._auth.add_password(None, self.api, user, password)
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(self._auth))

    def _pages(self, path: str, query: dict | None = None) -> list:
        out, page = [], 1
        while True:
            params = {**(query or {}), "page": page, "page_size": PAGE_SIZE}
            url = f"{self.api}{path}?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            try:
                with self._opener.open(request, timeout=60) as response:
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                raise CensusError(f"Harbor GET {path}: HTTP {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise CensusError(f"Harbor GET {path}: {exc}") from exc
            batch = json.loads(raw) if raw else []
            out += batch
            if len(batch) < PAGE_SIZE:
                return out
            page += 1

    def projects(self) -> list[str]:
        return [p["name"] for p in self._pages("/projects")]

    def repositories(self, project: str) -> list[str]:
        # Harbor returns "project/repo"; the artifact path wants the repo part alone, escaped.
        return [r["name"].split("/", 1)[1] for r in
                self._pages(f"/projects/{urllib.parse.quote(project, safe='')}/repositories")
                if "/" in r["name"]]

    def artifacts(self, project: str, repository: str) -> list[dict]:
        path = (f"/projects/{urllib.parse.quote(project, safe='')}"
                f"/repositories/{urllib.parse.quote(repository, safe='')}/artifacts")
        return self._pages(path, {"q": "type=IMAGE", "with_tag": "true"})


def walk(harbor, projects: list[str] | None = None) -> list[dict]:
    """Every image artifact in the fleet, as `{project, repository, digest, tags, annotations}`.

    An artifact with no digest is dropped: Harbor has nothing we can key on, and inventing a
    key would put a phantom in the count.
    """
    fleet = []
    for project in projects or harbor.projects():
        for repository in harbor.repositories(project):
            for artifact in harbor.artifacts(project, repository):
                digest = artifact.get("digest")
                if not digest:
                    continue
                fleet.append({
                    "project": project,
                    "repository": f"{project}/{repository}",
                    "digest": digest,
                    "tags": [t.get("name") for t in artifact.get("tags") or []],
                    "annotations": artifact.get("annotations") or {},
                })
    return fleet


# --- subtract -------------------------------------------------------------------------------


def suspects(fleet: list[dict], known_repositories: set[str] | None = None) -> list[dict]:
    """The fleet minus what came through a door: stamped by knock, or owned by the existing
    chain (D-26 — an image the existing chain admitted has bypassed nothing).

    `known_repositories` are `project/repo` names, the list IF-08 owes us and that gap 14
    says nobody produces yet. Absent, everything unstamped is suspect, which over-counts by
    exactly the size of the existing chain — stated in the report, never silently.
    """
    known = known_repositories or set()
    return [a for a in fleet
            if STAMP_KEY not in a["annotations"] and a["repository"] not in known]


# --- ask ------------------------------------------------------------------------------------

Ask = Callable[[dict], dict]


def command_oracle(command: str, timeout: int = 30) -> Ask:
    """The usage oracle as `knock` speaks it: the JSON query on stdin, `{"last_seen": ...}` on
    stdout, exit 0 to answer. The very command the house retention already runs."""
    argv = shlex.split(command)
    if not argv:
        raise CensusError("empty oracle command")

    def ask(query: dict) -> dict:
        try:
            done = subprocess.run(argv, input=json.dumps(query), capture_output=True,
                                  text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CensusError(str(exc)) from exc
        if done.returncode != 0:
            raise CensusError(f"oracle failed: {done.stderr.strip()}")
        try:
            answer = json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise CensusError(f"oracle: invalid JSON: {exc}") from exc
        if not isinstance(answer, dict):
            raise CensusError(f"oracle: expected an object, got {answer!r}")
        return answer

    return ask


def in_service(suspect: list[dict], ask: Ask, *, idle_days: int = HOUSE_IDLE_DAYS,
               now: datetime | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Split the suspects into (seen, unseen, unknown) by asking the oracle one digest at a time.

    An oracle that errors, times out or answers unreadably puts its digest in `unknown` — never
    in `unseen`. That is the inverse of `knock purge`'s fail-closed, and deliberate: there,
    silence must protect an image; here, silence must not shrink a count.
    """
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=idle_days)
    seen, unseen, unknown = [], [], []
    for artifact in suspect:
        query = {"digest": artifact["digest"],
                 "image_ref": f"{artifact['repository']}:{(artifact['tags'] or ['<untagged>'])[0]}",
                 "identity": {"policy": None, "import": None, "variant": None},
                 "since": since.isoformat()}
        try:
            answer = ask(query)
            last_seen = _timestamp(answer.get("last_seen"))
        except CensusError as exc:
            unknown.append({**artifact, "reason": str(exc)})
            continue
        if last_seen is None:
            unseen.append(artifact)
        else:
            seen.append({**artifact, "last_seen": last_seen.isoformat(),
                         "detail": str(answer.get("detail", ""))})
    return seen, unseen, unknown


def _timestamp(value) -> datetime | None:
    """`null` or absent means genuinely unseen. A malformed value raises rather than pass for
    one: a bad string must not read as "nobody runs this"."""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise CensusError(f"oracle: invalid last_seen {value!r}")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CensusError(f"oracle: invalid last_seen {value!r}: {exc}") from exc


# --- the count ------------------------------------------------------------------------------


def report(fleet: list[dict], suspect: list[dict], split=None, *,
           idle_days: int = HOUSE_IDLE_DAYS, known_repositories: set[str] | None = None) -> dict:
    """The census: a count, and everything that bounds it.

    `split` is `in_service`'s triple, or None when no oracle was given — then only the stored
    bypass is reported, and the in-service question stays open rather than being answered by
    default.
    """
    stamped = len(fleet) - len(suspect) - _unstamped_but_known(fleet, known_repositories)
    caveats = []
    if not known_repositories:
        caveats.append("no existing-chain repository list (IF-08, gap 14): the suspect set "
                       "still holds everything that chain admitted, so the bypass is an "
                       "upper bound, not the number")
    if fleet and stamped == 0:
        caveats.append("not one artifact in the fleet carries the knock stamp: either nothing "
                       "has been placed yet, or Harbor is not returning manifest annotations — "
                       "check before reading the rate")
    out = {
        "fleet": len(fleet),
        "suspect": len(suspect),
        "idle_days": idle_days,
        "caveats": caveats,
    }
    if split is None:
        out["bypass_stored"] = len(suspect)
        out["bypass_in_service"] = None  # not asked, so not answered
        return out
    seen, unseen, unknown = split
    out["bypass_stored"] = len(suspect)
    out["bypass_in_service"] = len(seen)
    out["not_in_service"] = len(unseen)
    out["unknown"] = len(unknown)
    answered = len(seen) + len(unseen)
    out["rate_in_service"] = round(len(seen) / len(fleet), 4) if fleet else None
    out["bound"] = {"low": len(seen), "high": len(seen) + len(unknown)}
    if unknown:
        caveats.append(f"{len(unknown)} of {len(suspect)} suspects went unanswered by the "
                       f"oracle: the count is between {len(seen)} and {len(seen) + len(unknown)}")
    if suspect and answered == 0:
        caveats.append("the oracle answered nothing at all: the census has no in-service "
                       "figure, only the stored bypass")
    return out


def _unstamped_but_known(fleet: list[dict], known_repositories: set[str] | None) -> int:
    known = known_repositories or set()
    return sum(1 for a in fleet
               if STAMP_KEY not in a["annotations"] and a["repository"] in known)
