"""CLI smoke tests and report/figure rendering from the committed results."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_ops_twin.cli import main
from agentic_ops_twin.decision.study import DecisionStudy
from agentic_ops_twin.reporting.research_report import render_research
from agentic_ops_twin.reporting.study_report import render_study

RESULTS = Path(__file__).resolve().parents[1] / "results"


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    try:
        main(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    return capsys.readouterr().out


def test_cli_offline_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger = ["--ledger", str(tmp_path / "l.sqlite")]
    assert "insurance" in run(["packs"], capsys)
    assert "OK" in run(["validate", "--pack", "procurement"], capsys)
    sim = json.loads(run(["simulate", "--pack", "support", "--seed", "3"], capsys))
    assert sim["arrivals"] == sim["completed"] + sim["open"]
    out = run(
        [*ledger, "propose", "--pack", "insurance", "Skip the fraud check under normal demand."],
        capsys,
    )
    assert "control_locked" in out
    out = run(
        [*ledger, "propose", "--pack", "insurance", "Add 1 adjuster under normal demand."], capsys
    )
    assert "validated change set" in out
    out = run([*ledger, "eval-agent", "--limit", "4", "--out", str(tmp_path)], capsys)
    assert "scripted-fake-v1" in out
    assert (tmp_path / "agent" / "eval-fake.md").exists()
    out = run(
        ["dataset", "--pack", "procurement", "--seed", "1", "--out", str(tmp_path / "d")], capsys
    )
    assert "exported" in out
    assert "verified" in run([*ledger, "ledger", "verify"], capsys)


def test_cli_rejects_real_provider_without_cap(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit, match="max-cost-usd"):
        main(["propose", "--pack", "insurance", "x", "--provider", "anthropic"])


def test_validate_model_file_reports_rejection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "m.json"
    bad.write_text('{"id": "x"}', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["validate", "--model-file", str(bad)])
    assert exc.value.code == 1
    assert "REJECTED" in capsys.readouterr().out


@pytest.mark.parametrize("pack", ["insurance", "procurement", "support"])
def test_study_report_renders_from_committed_results(pack: str) -> None:
    study = DecisionStudy.model_validate_json(
        (RESULTS / pack / "study-full.json").read_text(encoding="utf-8")
    )
    md = render_study(study)
    assert "## Held-out evaluation" in md and "Pairing verification" in md


def test_research_report_renders_from_committed_results() -> None:
    packs = {
        p: json.loads((RESULTS / p / "research.json").read_text(encoding="utf-8"))
        for p in ("insurance", "procurement", "support")
    }
    md = render_research(
        {
            "preregistration_sha256": "0" * 64,
            "preregistration_record": "r",
            "quick": False,
            "packs": packs,
        }
    )
    assert "H1" in md and "Residual diagnostics" in md


def test_figures_render(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from agentic_ops_twin.reporting import figures

    paths = [
        figures.fig_decision_quality(RESULTS, tmp_path, "light"),
        figures.fig_calibrated_but_wrong(RESULTS, tmp_path, "dark"),
        figures.fig_ranking_validity(RESULTS, tmp_path, "light"),
        figures.fig_downstream_shift(RESULTS, tmp_path, "dark"),
    ]
    for p in paths:
        text = p.read_text(encoding="utf-8")
        assert text.startswith("<?xml") and "<svg" in text


def test_research_helpers() -> None:
    from agentic_ops_twin.research.runner import _tau

    assert _tau({"a": 1, "b": 2, "c": 3}, {"a": 10, "b": 20, "c": 30}) == pytest.approx(1.0)
    assert _tau({"a": 1, "b": 2}, {"a": 1, "b": 2}) is None


@pytest.mark.slow
def test_research_runner_quick_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_ops_twin.governance.ledger import Ledger
    from agentic_ops_twin.research.runner import run_research

    monkeypatch.chdir(RESULTS.parent)  # pre-registration is read from docs/
    ledger = tmp_path / "l.sqlite"
    run_research(("procurement",), out=tmp_path, ledger_path=str(ledger), workers=None, quick=True)
    report = json.loads((tmp_path / "procurement" / "research-quick.json").read_text())
    assert {"hidden_truth", "selection", "robust"} <= set(report)
    kinds = [r.kind for r in Ledger(ledger).records()]
    assert kinds[0] == "preregistration" and "experiment" in kinds
    assert (tmp_path / "research-quick.md").exists()
