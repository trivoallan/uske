"""Feed Dependency-Track the inventories knock signed: the rapprochement of rhythm 2 (D-20).

The fleet is read from the registry (`knock audit`), never from the journal. `plan` is pure;
the Dependency-Track client and cosign sit behind small seams so tests replace them.
Change `dt-sync`, design decisions 3 to 7.
"""

from __future__ import annotations

import base64
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from uske.policies import Policy

# knock audit's CoverageReport, a published contract since knock 0.12.0 (additive within a version).
AUDIT_API = ("knock.io/v1alpha1", "CoverageReport")
AUDIT_FIELDS = ("image_ref", "digest", "covered", "signed", "sbom", "sbom_formats", "policy")
SBOM_FORMAT = "cyclonedx-json"  # what Dependency-Track reads
MANAGED_TAG = "dt-sync"  # every project dt-sync writes carries it: the only ones it may retire
DIGEST_GROUP, DIGEST_NAME = "oci", "digest"
CYCLONEDX = "https://cyclonedx.org/bom"


class SyncError(Exception):
    """A technical failure: bad input, Dependency-Track or cosign unusable."""


# --- the diff -----------------------------------------------------------------------------------


def placed(audit: dict) -> list[dict]:
    """knock audit's outcomes that are stamped, signed and carry an SBOM. Another report version,
    or a missing field, fails: better no send than a wrong one."""
    if not isinstance(audit, dict) or (audit.get("apiVersion"), audit.get("kind")) != AUDIT_API:
        found = (audit.get("apiVersion"), audit.get("kind")) if isinstance(audit, dict) else None
        raise SyncError(f"knock audit: expected {AUDIT_API}, got {found}")
    outcomes = audit.get("outcomes")
    if not isinstance(outcomes, list):
        raise SyncError("knock audit: no outcomes list")
    fleet = []
    for outcome in outcomes:
        if outcome.get("error"):
            continue  # an unreadable image is knock's to report, not ours to guess
        missing = [f for f in AUDIT_FIELDS if f not in outcome]
        if missing:
            raise SyncError(f"knock audit: {outcome.get('image_ref', '?')} lacks {', '.join(missing)}")
        if outcome["covered"] and outcome["signed"] and outcome["sbom"]:
            fleet.append(outcome)
    return fleet


def identity(image_ref: str) -> tuple[str, str, str]:
    """`host/path/repo:tag` -> (`host/path/repo`, project `path/repo`, version `tag`)."""
    repository, _, tag = image_ref.rpartition(":")
    if not repository or "/" in tag:
        raise SyncError(f"{image_ref}: no tag")
    return repository, repository.split("/", 1)[1], tag


def owners(policy: Policy) -> list[str]:
    found = []
    for imp in (policy.document.get("spec") or {}).get("imports") or []:
        for owner in imp.get("owners") or []:
            if owner not in found:
                found.append(owner)
    return found


def tags(policy_name: str, policy: Policy | None) -> list[str]:
    """Filterable in Dependency-Track, and a notification rule can select on them (decision 5).
    Lower case: Dependency-Track lowers tags itself."""
    out = [MANAGED_TAG, f"policy:{policy_name}"]
    if policy is not None:
        if policy.track:
            out.append(f"track:{policy.track}")
        out += [f"owner:{o}" for o in owners(policy)]
    return [t.lower() for t in out]


def plan(fleet: list[dict], policies: dict[str, Policy], tracked: list[dict]) -> dict:
    """What to send, what to retire, what to report.

    `tracked`: the versions dt-sync wrote, as {uuid, project, version, digest, active}.
    """
    by_key = {(t["project"], t["version"]): t for t in tracked}
    send, report, seen = [], [], set()
    for image in fleet:
        repository, project, version = identity(image["image_ref"])
        seen.add((project, version))
        if SBOM_FORMAT not in (image["sbom_formats"] or []):
            # placed before knock emitted CycloneDX: reported every pass, never sent (spec)
            report.append({"ref": image["image_ref"], "reason": "no-cyclonedx"})
            continue
        policy = policies.get(image["policy"])
        if policy is None:
            report.append({"ref": image["image_ref"], "reason": "unknown-policy", "policy": image["policy"]})
        known = by_key.get((project, version))
        if known and known["digest"] == image["digest"] and known["active"]:
            continue
        send.append({
            "ref": repository,
            "digest": image["digest"],
            "project": project,
            "version": version,
            "tags": tags(image["policy"], policy),
            "uuid": known["uuid"] if known else None,
        })
    retire = [
        {"uuid": t["uuid"], "project": t["project"], "version": t["version"]}
        for t in tracked
        if t["active"] and (t["project"], t["version"]) not in seen
    ]
    return {"send": send, "retire": retire, "report": report}


# --- Dependency-Track ---------------------------------------------------------------------------


class DependencyTrack:
    def __init__(self, url: str, key: str):
        self.api = url.rstrip("/") + "/api"
        self.key = key

    def call(self, method: str, path: str, body=None, query: dict | None = None):
        url = self.api + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            "X-Api-Key": self.key, "Content-Type": "application/json", "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise SyncError(f"Dependency-Track {method} {path}: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise SyncError(f"Dependency-Track {method} {path}: {exc}") from exc
        return json.loads(raw) if raw else None

    def tracked(self) -> list[dict]:
        # ponytail: one property call per version; fine for a pilot's fleet, batch if it grows
        out, page = [], 1
        while True:
            projects = self.call("GET", f"/v1/project/tag/{MANAGED_TAG}", query={"pageNumber": page, "pageSize": 100})
            for p in projects or []:
                properties = self.call("GET", f"/v1/project/{p['uuid']}/property") or []
                digest = next((x.get("propertyValue") for x in properties
                               if x.get("groupName") == DIGEST_GROUP and x.get("propertyName") == DIGEST_NAME), None)
                out.append({"uuid": p["uuid"], "project": p["name"], "version": p.get("version"),
                            "digest": digest, "active": p.get("active", True)})
            if not projects or len(projects) < 100:
                return out
            page += 1

    def publish(self, item: dict, bom: dict) -> str:
        uploaded = self.call("PUT", "/v1/bom", {
            "projectName": item["project"],
            "projectVersion": item["version"],
            "autoCreate": True,
            "projectTags": [{"name": t} for t in item["tags"]],
            "bom": base64.b64encode(json.dumps(bom).encode()).decode(),
        })
        uuid = item.get("uuid") or (uploaded or {}).get("projectUuid")
        if not uuid:
            raise SyncError(f"{item['project']} {item['version']}: no project uuid after upload")
        # an existing version keeps its old tags and state through a BOM upload: set them
        self.call("PATCH", f"/v1/project/{uuid}", {"active": True, "tags": [{"name": t} for t in item["tags"]]})
        prop = {"groupName": DIGEST_GROUP, "propertyName": DIGEST_NAME,
                "propertyValue": item["digest"], "propertyType": "STRING"}
        try:
            self.call("PUT", f"/v1/project/{uuid}/property", prop)  # create
        except SyncError as exc:
            if "HTTP 409" not in str(exc):
                raise
            self.call("POST", f"/v1/project/{uuid}/property", prop)  # already there: update
        return uuid

    def retire(self, uuid: str) -> None:
        self.call("PATCH", f"/v1/project/{uuid}", {"active": False})


# --- cosign -------------------------------------------------------------------------------------

Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=300)


def verified_bom(ref: str, key: str, registry_flags: list[str], run: Runner = _run) -> dict:
    """The CycloneDX predicate knock signed for `ref` (pinned by digest). The plan only sends
    images whose audit lists a CycloneDX SBOM, so any failure here is a signal, never skipped."""
    # A key signature carries no Rekor entry: skip the tlog check, as knock's own verify does.
    verify = run(["cosign", "verify-attestation", "--key", key, "--insecure-ignore-tlog=true",
                  "--type", "cyclonedx", "--new-bundle-format", *registry_flags, ref])
    if verify.returncode != 0:
        raise SyncError(f"{ref}: CycloneDX attestation not verified with {key}: {verify.stderr.strip()[-300:]}")
    line = verify.stdout.strip().splitlines()[0]
    return json.loads(base64.b64decode(json.loads(line)["payload"]))["predicate"]
