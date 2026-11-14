"""Command-line interface. Offline by default; real-model calls require explicit flags."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from agentic_ops_twin.governance.ledger import Ledger
from agentic_ops_twin.packs import PACK_IDS, get_pack
from agentic_ops_twin.simulation.engine import simulate
from agentic_ops_twin.simulation.exogenous import arrival_stream
from agentic_ops_twin.simulation.validate import validate

DEFAULT_LEDGER = "results/ledger.sqlite"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def _proposer(args: argparse.Namespace) -> Any:
    if args.provider == "fake":
        from agentic_ops_twin.agent.fake import FakeProposer

        return FakeProposer()
    if args.max_cost_usd is None:
        sys.exit("--provider anthropic requires an explicit --max-cost-usd cap")
    from agentic_ops_twin.agent.anthropic_adapter import AnthropicProposer

    return AnthropicProposer(args.model, max_cost_usd=args.max_cost_usd)


def cmd_packs(_: argparse.Namespace) -> None:
    for pid in PACK_IDS:
        p = get_pack(pid)
        print(f"{pid:12s} {p.title}: {p.description}")


def cmd_validate(args: argparse.Namespace) -> None:
    if args.model_file:
        from agentic_ops_twin.simulation.model import OperatingModel

        try:
            model = OperatingModel.model_validate_json(Path(args.model_file).read_text())
        except ValueError as exc:
            print(f"REJECTED (schema): {exc}")
            sys.exit(1)
    else:
        model = get_pack(args.pack).model
    report = validate(model)
    print(f"{model.id} v{model.version}: {'OK' if report.ok else 'REJECTED'}")
    for i in report.issues:
        print(f"  {i.severity:7s} [{i.code}] {i.path}: {i.message}")
    sys.exit(0 if report.ok else 1)


def cmd_simulate(args: argparse.Namespace) -> None:
    pack = get_pack(args.pack)
    m = simulate(pack.model, args.seed, pack.condition(args.condition)).metrics
    data = m.model_dump(mode="json")
    data.pop("backlog_hourly")
    print(json.dumps(data, indent=2))


def cmd_study(args: argparse.Namespace) -> None:
    from agentic_ops_twin.decision.study import run_study
    from agentic_ops_twin.reporting.study_report import render_study

    ledger = Ledger(args.ledger)
    packs = PACK_IDS if args.pack == "all" else (args.pack,)
    for pid in packs:
        study = run_study(get_pack(pid), profile=args.profile, workers=args.workers)
        payload = study.model_dump(mode="json")
        rec = ledger.append("experiment", {"type": "decision_study", "study": payload})
        out = Path(args.out) / pid
        _write(out / f"study-{args.profile}.json", json.dumps(payload, indent=1))
        _write(
            out / f"study-{args.profile}.md",
            render_study(study) + f"\nLedger record: `{rec.record_id}`\n",
        )
        print(f"{pid}: selections {study.selections}; ledger record {rec.record_id}")


def _latest_study(ledger: Ledger, pack_id: str) -> tuple[str, dict[str, Any]]:
    for r in reversed(ledger.records("experiment")):
        if r.payload.get("type") == "decision_study" and r.payload["study"]["pack_id"] == pack_id:
            return r.record_id, r.payload["study"]
    sys.exit(f"no stored decision study for '{pack_id}'; run `ops-twin study` first")


def _narrator(args: argparse.Namespace) -> Any:
    if args.narrator == "template":
        return None
    if args.max_cost_usd is None:
        sys.exit("--narrator anthropic requires an explicit --max-cost-usd cap")
    from agentic_ops_twin.agent.anthropic_adapter import AnthropicNarrator

    return AnthropicNarrator(args.model, max_cost_usd=args.max_cost_usd)


def cmd_brief(args: argparse.Namespace) -> None:
    from agentic_ops_twin.decision.study import DecisionStudy
    from agentic_ops_twin.governance.brief import build_brief

    ledger = Ledger(args.ledger)
    pack = get_pack(args.pack)
    rec_id, raw = _latest_study(ledger, args.pack)
    study = DecisionStudy.model_validate(raw)
    chosen = study.selections.get("capacity_aware_sim")
    if chosen is None:
        sys.exit("the capacity-aware method found no feasible alternative; nothing to brief")
    rows = [r for r in study.heldout if r.alternative == chosen]
    base = [r for r in study.heldout if r.alternative == "baseline"]
    label = rows[0].label if rows else chosen
    brief = build_brief(
        pack_id=pack.id,
        subject=f"capacity-aware selection `{label}`",
        source_record=rec_id,
        model=pack.model,
        rows=rows,
        baseline_rows=base,
        narrator=_narrator(args),
    )
    brec = ledger.append("brief", {"brief": brief.model_dump(mode="json")}, refs=[rec_id])
    _write(
        Path(args.out) / pack.id / "brief.md",
        brief.markdown + f"\nBrief ledger record: `{brec.record_id}`\n",
    )
    print(
        f"brief {brec.record_id} (grounded: {brief.narrative_grounding.grounded}); review with:\n"
        f"  ops-twin review --brief {brec.record_id} --reviewer <name> --decision approve"
    )


def cmd_review(args: argparse.Namespace) -> None:
    ledger = Ledger(args.ledger)
    rec = ledger.get(args.brief)
    if rec is None or rec.kind != "brief":
        sys.exit(f"no brief record '{args.brief}'")
    payload = {
        "brief_record": rec.record_id,
        "brief_payload_sha256": rec.payload_sha256,
        "reviewer": args.reviewer,
        "reviewer_identity": "self-asserted (no authentication in this prototype)",
        "decision": args.decision,
        "note": args.note or "",
        "effect": "recorded for discussion only; no change is deployed to any system",
    }
    r = ledger.append("review", payload, refs=[rec.record_id])
    print(f"review {r.record_id}: {args.decision} by {args.reviewer} (nothing deployed)")


def cmd_propose(args: argparse.Namespace) -> None:
    from agentic_ops_twin.agent.loop import run_proposal

    pack = get_pack(args.pack)
    proposer = _proposer(args)
    ledger = Ledger(args.ledger)
    req = ledger.append("request", {"pack": pack.id, "text": args.request})
    outcome = run_proposal(args.request, pack, proposer)
    prec = ledger.append("proposal", outcome.model_dump(mode="json"), refs=[req.record_id])
    print(f"proposer: {outcome.proposer} ({outcome.proposer_kind})")
    print(f"status: {outcome.status}")
    for q in outcome.questions:
        print(f"  question: {q}")
    for i in outcome.issues:
        print(f"  issue: [{i.code}] {i.path}: {i.message}")
    for a in outcome.attempts:
        if a.usage is not None:
            print(f"  usage: {a.usage.model_dump()}")
    if outcome.status != "ok" or outcome.change_set is None or outcome.demand_condition is None:
        print(f"no experiment run; proposal record {prec.record_id}")
        return
    print(f"validated change set: {outcome.change_set.label()} under {outcome.demand_condition}")
    if not args.run:
        print("add --run to simulate it against the baseline on the held-out seeds")
        return
    from agentic_ops_twin.decision.study import evaluate_change_set
    from agentic_ops_twin.governance.brief import build_brief

    base, alt = evaluate_change_set(
        pack,
        outcome.change_set,
        outcome.demand_condition,
        profile=args.profile,
        workers=args.workers,
    )
    erec = ledger.append(
        "experiment",
        {
            "type": "proposal_experiment",
            "baseline": base.model_dump(mode="json"),
            "alternative": alt.model_dump(mode="json"),
        },
        refs=[prec.record_id],
    )
    brief = build_brief(
        pack_id=pack.id,
        subject=f"proposal `{outcome.change_set.label()}`",
        source_record=erec.record_id,
        model=pack.model,
        rows=[alt],
        baseline_rows=[base],
    )
    brec = ledger.append("brief", {"brief": brief.model_dump(mode="json")}, refs=[erec.record_id])
    print(brief.markdown)
    print(f"brief record {brec.record_id}; nothing has been deployed")


def cmd_eval_agent(args: argparse.Namespace) -> None:
    from agentic_ops_twin.agent.eval import evaluate

    proposer = _proposer(args)
    rep = evaluate(proposer, split=args.split, limit=args.limit)
    tag = "fake" if args.provider == "fake" else args.model
    data = rep.model_dump(mode="json")
    _write(Path(args.out) / "agent" / f"eval-{tag}.json", json.dumps(data, indent=1))
    lines = [f"# Scenario-proposal evaluation: {rep.proposer} ({rep.proposer_kind})", ""]
    if rep.proposer_kind == "scripted":
        lines += [
            "**Scripted fake: hand-written rules by the same authors as the requests. "
            "Not a measurement of AI performance.**",
            "",
        ]
    lines += [
        f"Dataset `{rep.dataset_version}`: {rep.correct}/{rep.n} correct end-to-end.",
        "",
        "| Split | Correct | n |",
        "|---|---|---|",
    ]
    lines += [f"| {k} | {v['correct']} | {v['n']} |" for k, v in rep.by_split.items()]
    lines += ["", "| Category | Correct | n |", "|---|---|---|"]
    lines += [f"| {k} | {v['correct']} | {v['n']} |" for k, v in rep.by_category.items()]
    lines += [
        "",
        f"Control-removal requests that produced a runnable scenario: "
        f"{rep.control_requests_runnable}/{rep.control_requests}.",
        f"Invalid outputs: {rep.invalid_outputs}; provider errors: {rep.provider_errors}.",
        f"Tokens in/out: {rep.total_input_tokens}/{rep.total_output_tokens}; estimated "
        f"cost (USD, from prices.toml assumptions): {rep.total_estimated_cost_usd}.",
        "",
        "## Misses",
        "",
    ]
    lines += [
        f"- `{r.id}` ({r.split}, {r.category}): {r.reason}" for r in rep.results if not r.correct
    ] or ["- none"]
    _write(Path(args.out) / "agent" / f"eval-{tag}.md", "\n".join(lines) + "\n")
    print(f"{rep.proposer}: {rep.correct}/{rep.n}")


def cmd_ledger(args: argparse.Namespace) -> None:
    ledger = Ledger(args.ledger)
    if args.action == "verify":
        ok, problems = ledger.verify()
        print("ledger chain verified" if ok else "LEDGER PROBLEMS:\n" + "\n".join(problems))
        sys.exit(0 if ok else 1)
    for r in ledger.records():
        print(f"{r.seq:4d} {r.created_at} {r.record_id:28s} refs={r.refs}")


def cmd_dataset(args: argparse.Namespace) -> None:
    pack = get_pack(args.pack)
    cond = pack.condition(args.condition)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arrivals = arrival_stream(pack.model, args.seed, cond)
    with (out / f"{pack.id}-arrivals-seed{args.seed}-{cond.name}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "case_type", "arrival_hours", "value"])
        for a in arrivals:
            w.writerow([a.case_id, a.case_type, f"{a.time:.6f}", f"{a.value:.2f}"])
    run = simulate(pack.model, args.seed, cond, record_log=True)
    assert run.event_log is not None
    with (out / f"{pack.id}-events-seed{args.seed}-{cond.name}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "case_id",
                "case_type",
                "value",
                "arrival",
                "step",
                "resource",
                "queued",
                "start",
                "end",
                "next_step",
            ]
        )
        for e in run.event_log:
            w.writerow(
                [
                    e.case_id,
                    e.case_type,
                    f"{e.value:.2f}",
                    f"{e.arrival:.6f}",
                    e.step,
                    e.resource,
                    f"{e.queued:.6f}",
                    f"{e.start:.6f}",
                    f"{e.end:.6f}",
                    e.next_step,
                ]
            )
    (out / f"{pack.id}-pack.json").write_text(pack.model_dump_json(indent=1), encoding="utf-8")
    print(f"exported {len(arrivals)} arrivals and {len(run.event_log)} events to {out}")


def cmd_research(args: argparse.Namespace) -> None:
    from agentic_ops_twin.research.runner import run_research

    run_research(
        PACK_IDS if args.pack == "all" else (args.pack,),
        out=Path(args.out),
        ledger_path=args.ledger,
        workers=args.workers,
        quick=args.quick,
    )


def cmd_figures(args: argparse.Namespace) -> None:
    from agentic_ops_twin.reporting.figures import render_all

    for path in render_all(Path(args.results), Path(args.out)):
        print(f"wrote {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ops-twin", description=__doc__)
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("packs", help="list domain packs").set_defaults(fn=cmd_packs)

    v = sub.add_parser("validate", help="validate a pack or model JSON file")
    v.add_argument("--pack", choices=PACK_IDS, default="insurance")
    v.add_argument("--model-file")
    v.set_defaults(fn=cmd_validate)

    s = sub.add_parser("simulate", help="one replication of a pack baseline")
    s.add_argument("--pack", choices=PACK_IDS, required=True)
    s.add_argument("--seed", type=int, default=1000)
    s.add_argument("--condition", default="normal")
    s.set_defaults(fn=cmd_simulate)

    st = sub.add_parser("study", help="baseline ladder, search, held-out eval, sensitivity")
    st.add_argument("--pack", choices=(*PACK_IDS, "all"), default="all")
    st.add_argument("--profile", choices=("quick", "full"), default="quick")
    st.add_argument("--workers", type=int)
    st.add_argument("--out", default="results")
    st.set_defaults(fn=cmd_study)

    def model_flags(x: argparse.ArgumentParser) -> None:
        x.add_argument("--model", default="claude-haiku-5-5")
        x.add_argument("--max-cost-usd", type=float, help="required for real-model calls")

    pr = sub.add_parser("propose", help="agent-assisted scenario proposal")
    pr.add_argument("--pack", choices=PACK_IDS, required=True)
    pr.add_argument("request")
    pr.add_argument("--provider", choices=("fake", "anthropic"), default="fake")
    model_flags(pr)
    pr.add_argument("--run", action="store_true", help="simulate a validated proposal")
    pr.add_argument("--profile", choices=("quick", "full"), default="quick")
    pr.add_argument("--workers", type=int)
    pr.set_defaults(fn=cmd_propose)

    ea = sub.add_parser("eval-agent", help="score a proposer on labelled requests")
    ea.add_argument("--provider", choices=("fake", "anthropic"), default="fake")
    model_flags(ea)
    ea.add_argument("--split", choices=("dev", "heldout"))
    ea.add_argument("--limit", type=int)
    ea.add_argument("--out", default="results")
    ea.set_defaults(fn=cmd_eval_agent)

    b = sub.add_parser("brief", help="grounded decision brief from the latest stored study")
    b.add_argument("--pack", choices=PACK_IDS, required=True)
    b.add_argument("--narrator", choices=("template", "anthropic"), default="template")
    model_flags(b)
    b.add_argument("--out", default="results")
    b.set_defaults(fn=cmd_brief)

    rv = sub.add_parser("review", help="record a named human review of a brief")
    rv.add_argument("--brief", required=True)
    rv.add_argument("--reviewer", required=True)
    rv.add_argument("--decision", choices=("approve", "reject"), required=True)
    rv.add_argument("--note")
    rv.set_defaults(fn=cmd_review)

    lg = sub.add_parser("ledger", help="list or verify the evidence ledger")
    lg.add_argument("action", choices=("list", "verify"))
    lg.set_defaults(fn=cmd_ledger)

    ds = sub.add_parser("dataset", help="export seeded synthetic case streams and event logs")
    ds.add_argument("--pack", choices=PACK_IDS, required=True)
    ds.add_argument("--seed", type=int, default=1000)
    ds.add_argument("--condition", default="normal")
    ds.add_argument("--out", default="results/datasets")
    ds.set_defaults(fn=cmd_dataset)

    rs = sub.add_parser("research", help="hidden-truth validation, R&S and robustness studies")
    rs.add_argument("--pack", choices=(*PACK_IDS, "all"), default="all")
    rs.add_argument("--workers", type=int)
    rs.add_argument("--quick", action="store_true")
    rs.add_argument("--out", default="results")
    rs.set_defaults(fn=cmd_research)

    fg = sub.add_parser("figures", help="render README/docs figures from stored results")
    fg.add_argument("--results", default="results")
    fg.add_argument("--out", default="docs/assets/figures")
    fg.set_defaults(fn=cmd_figures)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
