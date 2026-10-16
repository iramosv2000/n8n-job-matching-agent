import json
from pathlib import Path

import pytest

from matcher.regions import extract_region

CASES = json.loads((Path(__file__).parent / "fixtures" / "region_parity.json").read_text(encoding="utf-8"))[
    "cases"
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["location"][:40] or "<empty>")
def test_parity_with_as_is_tool(case):
    """Expected values were produced by the original analisis.extraer_region."""
    assert extract_region(case["location"]) == case["region"]


def test_last_segment_wins_over_street_names():
    assert extract_region("Lautaro 123, Santiago") == "Metropolitana"
