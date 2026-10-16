"""The reasons page is generated from the code, and the code writes no reason it does not list."""

import re
import unittest
from pathlib import Path

from uske import outcomes

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "reference" / "raisons.md"


class ReasonsTest(unittest.TestCase):
    def test_every_reason_literal_is_documented(self):
        # a quoted `uske/...` or `regis/...` is a reason; an f-string keeps its fixed prefix
        codes = [r.code for r in outcomes.REASONS]
        for path in sorted((ROOT / "uske").glob("*.py")):
            for literal in re.findall(
                r"[\"']((?:uske|regis)/[a-z0-9-]+)", path.read_text()
            ):
                with self.subTest(path=path.name, reason=literal):
                    self.assertTrue(any(c.startswith(literal) for c in codes))

    def test_the_page_is_up_to_date(self):
        self.assertEqual(
            PAGE.read_text(),
            outcomes.reference(),
            "regenerate: uv run python -m uske.outcomes > docs/reference/raisons.md",
        )
