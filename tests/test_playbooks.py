"""The playbook is named after the regime; uske reads only tier ids and `curable` (playbook-routing)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import yaml

from uske import cli, outcomes, playbooks

FIXTURES = Path(__file__).parent / "fixtures" / "repo" / "playbooks"


def playbook(*tiers: dict, rules: list[dict] | None = None) -> dict:
    return {
        "apiVersion": "regis.io/v1alpha1",
        "kind": "Playbook",
        "spec": {"tiers": list(tiers), "rules": rules or []},
    }


def tier(name: str, tier_id: str | None = None) -> dict:
    return {"name": name, **({"id": tier_id} if tier_id else {}), "condition": True}


class Directory(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def write(self, name: str, doc) -> Path:
        path = self.root / name
        path.write_text(doc if isinstance(doc, str) else yaml.safe_dump(doc))
        return path


class Resolve(Directory):
    def test_present_regime(self):
        path = self.write("derogation.yaml", playbook())
        self.assertEqual(playbooks.resolve("derogation", self.root), path.resolve())

    def test_new_regime_needs_no_code(self):
        """*Nouveau régime*."""
        path = self.write("experimental.yaml", playbook())
        self.assertEqual(playbooks.resolve("experimental", self.root), path.resolve())

    def test_unknown_or_absent_regime(self):
        for track in ("standrad", None, ""):
            with self.subTest(track=track):
                self.assertIsNone(playbooks.resolve(track, self.root))

    def test_a_regime_is_never_a_path(self):
        """*Tentative de sortie du répertoire*."""
        outside = self.root.parent / "x.yaml"
        outside.write_text("kind: Playbook\n")
        self.addCleanup(outside.unlink)
        for track in ("../x", "../secrets/x", "/etc/passwd", "Standard", "a.b"):
            with self.subTest(track=track):
                self.assertIsNone(playbooks.resolve(track, self.root))


class Check(Directory):
    def assertRefused(self, *names: str) -> None:
        with self.assertRaises(playbooks.PlaybookError) as caught:
            playbooks.check(self.root)
        for name in names:
            self.assertIn(name, str(caught.exception))

    def test_the_fixture_playbooks_pass(self):
        playbooks.check(FIXTURES)

    def test_a_tier_without_id(self):
        """*Tier sans identifiant*."""
        self.write("standard.yaml", playbook(tier("Quarantaine")))
        self.assertRefused("standard.yaml", "Quarantaine")

    def test_an_unknown_or_reserved_id(self):
        """*Identifiant inconnu*, *Identifiant réservé*."""
        for tier_id in ("reject", "inconclusive"):
            with self.subTest(tier_id=tier_id):
                self.write("standard.yaml", playbook(tier("T", tier_id)))
                self.assertRefused("standard.yaml", "'T'")

    def test_a_file_that_is_no_playbook(self):
        """*Fichier qui n'est pas un playbook*."""
        for content in ("kind: MirrorPolicy\n", "a: [\n", "- just\n- a list\n"):
            with self.subTest(content=content):
                self.write("derogation.yaml", content)
                self.assertRefused("derogation.yaml")

    def test_nested_playbooks_are_not_routed(self):
        (self.root / "admission").mkdir()
        self.write("admission/playbook.yaml", playbook(tier("No id")))
        playbooks.check(self.root)

    def test_list_fails_before_listing(self):
        self.write("standard.yaml", playbook(tier("Quarantaine")))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cli.main(
                ["list", "--policies", str(self.root), "--playbooks", str(self.root)]
            )
        self.assertEqual(code, 1)
        self.assertIn("Quarantaine", err.getvalue())


class Curable(unittest.TestCase):
    def test_only_rules_tagged_curable(self):
        doc = playbook(
            rules=[
                {"slug": "cve-critical", "tags": ["version", "curable"]},
                {"slug": "no-root", "tags": ["version", "reparable"]},
                {"slug": "untagged"},
            ]
        )
        self.assertEqual(playbooks.curable(doc), {"cve-critical"})

    def test_the_fixture_regimes(self):
        """*Même règle, régimes différents*."""
        load = lambda name: yaml.safe_load((FIXTURES / name).read_text())
        self.assertEqual(playbooks.curable(load("standard.yaml")), {"cve-critical"})
        self.assertEqual(playbooks.curable(load("redistribution.yaml")), frozenset())


class TierId(unittest.TestCase):
    def classify(self, result: dict):
        return outcomes.classify({"playbooks": [{"rules": [], **result}]}, {})

    def test_the_name_is_never_read(self):
        """*Libellé traduit*."""
        self.assertEqual(
            self.classify({"tier": "Quarantine", "tier_id": "quarantine"})[0],
            outcomes.Outcome.QUARANTINE,
        )

    def test_a_report_without_tier_id(self):
        """*Identifiant absent du rapport*."""
        for result in ({"tier": "Quarantaine"}, {"tier_id": "inconclusive"}):
            with self.subTest(result=result):
                self.assertEqual(
                    self.classify(result),
                    (outcomes.Outcome.INCONCLUSIVE, "regis/unknown-tier"),
                )


if __name__ == "__main__":
    unittest.main()
