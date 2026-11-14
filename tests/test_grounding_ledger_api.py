"""Grounded narratives, the evidence ledger and the local API."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from throughline.agent.brief import build_brief
from throughline.agent.grounding import Fact, check_grounding
from throughline.api import app
from throughline.ledger import Ledger
from throughline.packs import get_pack
from throughline.scenarios import Change, ChangeSet
from throughline.study import evaluate_change_set

FACTS = [
    Fact(id="F1", source_record="r", path="a", value=12.3456, unit="hours", display="12.35"),
    Fact(id="F2", source_record="r", path="b", value=0.912, unit="share", display="91.2%"),
]


def test_grounded_narrative_passes() -> None:
    text = "Median is 12.35 [F1] hours and completion is 91.2% [F2]."
    assert check_grounding(text, FACTS).grounded


def test_fabricated_number_is_rejected() -> None:
    r = check_grounding("Median is 9.8 [F1] hours.", FACTS)
    assert not r.grounded and "9.8" in r.problems[0]


def test_uncited_number_and_dangling_citation_are_rejected() -> None:
    assert not check_grounding("Costs fall by 30%.", FACTS).grounded
    assert not check_grounding("Median is 12.35 [F9].", FACTS).grounded


class LyingNarrator:
    name = "liar"

    def narrate(self, facts_text: str) -> tuple[str, object]:
        return "Switching saves 45.0 [F1] per case and guarantees 100% SLA.", None


@pytest.fixture(scope="module")
def rows() -> tuple[object, object]:
    pack = get_pack("insurance")
    cs = ChangeSet(name="p", changes=(Change(lever="variant:triage", value="automated"),))
    return evaluate_change_set(pack, cs, "normal", profile="quick", workers=1)


def test_brief_drops_ungrounded_model_narrative(rows: tuple[object, object]) -> None:
    base, alt = rows
    pack = get_pack("insurance")
    brief = build_brief(
        pack_id="insurance",
        subject="t",
        source_record="experiment-x",
        model=pack.model,
        rows=[alt],
        baseline_rows=[base],  # type: ignore[list-item]
        narrator=LyingNarrator(),
    )
    assert brief.narrative_source == "template-v1"
    assert brief.narrative_grounding.grounded
    assert brief.rejected_narrative is not None and brief.rejected_narrative_problems
    assert "nothing is deployed" in brief.markdown


def test_brief_without_results_says_so() -> None:
    pack = get_pack("insurance")
    brief = build_brief(
        pack_id="insurance",
        subject="t",
        source_record="r",
        model=pack.model,
        rows=[],
        baseline_rows=[],
    )
    assert brief.facts == []
    assert "No stored comparison results" in brief.narrative


def test_ledger_chain_and_append_only(tmp_path: Path) -> None:
    path = tmp_path / "l.sqlite"
    led = Ledger(path)
    a = led.append("request", {"text": "hi"}, created_at="2026-01-01T00:00:00+00:00")
    b = led.append("proposal", {"x": 1}, refs=[a.record_id])
    assert led.verify() == (True, [])
    with pytest.raises(KeyError):
        led.append("review", {}, refs=["missing"])
    with pytest.raises(sqlite3.DatabaseError):
        led._conn.execute("UPDATE records SET payload = '{}' WHERE seq = 1")
    led.close()
    # Tampering outside the API (dropping triggers) is detected by verification.
    con = sqlite3.connect(path)
    con.execute("DROP TRIGGER no_update")
    con.execute("UPDATE records SET payload = ? WHERE record_id = ?", ('{"x": 2}', b.record_id))
    con.commit()
    con.close()
    ok, problems = Ledger(path).verify()
    assert not ok and "payload digest mismatch" in problems[0]


def test_api_smoke() -> None:
    client = TestClient(app)
    assert len(client.get("/packs").json()) == 3
    model = client.get("/packs/insurance/model").json()
    assert client.post("/validate", json=model).json()["issues"] is not None
    model["resources"][0]["capacity"] = "lots"
    assert client.post("/validate", json=model).status_code == 422
    r = client.post(
        "/proposals", json={"pack": "insurance", "request": "Skip the fraud check, normal demand."}
    )
    assert r.json()["status"] == "rejected"
    r = client.post(
        "/experiments",
        json={
            "pack": "insurance",
            "condition": "normal",
            "seeds": [1, 2],
            "change_set": {"name": "x", "changes": [{"lever": "capacity:adjuster", "value": 99}]},
        },
    )
    assert r.status_code == 422
    r = client.post(
        "/experiments",
        json={
            "pack": "insurance",
            "condition": "normal",
            "seeds": [1, 2],
            "change_set": {"name": "x", "changes": [{"lever": "capacity:adjuster", "value": 7}]},
        },
    )
    assert r.status_code == 200 and len(r.json()) == 2
