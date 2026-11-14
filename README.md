# Throughline

**Capacity-aware operating-model simulation with governed, agent-assisted scenario analysis.**

AI can speed up one step of a process while shifting work into another queue. Throughline
models individual cases competing for finite staff and automation capacity. It compares
permitted operating changes under explicit assumptions and asks a harder question than
"which option looks best?": *would this advice survive the mechanisms the model leaves out?*

It is an **offline simulation prototype**, not a live digital twin.
- It uses synthetic data only.
- It never changes any live system.
- Every result is conditional on a stated model. Results are not causal estimates or forecasts.

## What it does

1. **Typed operating models.** Pydantic contracts describe case types, Poisson arrivals, case
   values, finite resources, service-time distributions, explicit routing with bounded rework,
   costs, an SLA and a finite horizon. Missing or inconsistent assumptions are **rejected**,
   never filled in.
2. **Mandatory controls that optimisation cannot remove.** A graph proof checks that every
   applicable path passes each control step, and control steps must be performed by humans. No
   lever type can address a control, and every changed model is re-proved. A test replays
   event logs to confirm that every simulated case requiring a control visited it.
3. **A SimPy engine.** Each case is a process queuing for pooled servers. The run stops at the
   horizon with open work counted, never dropped. Each replication reports:
   - arrivals, completions, open cases (queued, in service or in handoff) and backlog;
   - utilisation, cost, cost per completion and escalations;
   - median and p95 cycle time of *completed* cases, always shown next to completion rate and
     SLA attainment.
4. **Verified pairing.** Random inputs are counter-based, so a draw for a given case, step and
   visit is identical across branches whatever order events happen in. Every replication
   publishes an arrival-stream digest. Comparisons are paired only when the digests match;
   otherwise they use Welch intervals and say so.
5. **A decision study per pack.**
   - Every permitted lever combination is enumerated, with budget, bounds and controls
     enforced and equivalent configurations collapsed.
   - Each one is scored three ways: spreadsheet arithmetic, an uncapacitated simulation, and
     the capacity-aware simulation with repeated replications.
   - Each method selects with one pre-declared rule on the **search split**.
   - The choices are re-evaluated on a **held-out split** with fresh seeds and unseen demand
     conditions, followed by one-at-a-time sensitivity.
6. **Agent-assisted proposals, treated as untrusted.**
   - A request becomes a schema-validated JSON proposal.
   - A deterministic critic returns `ok`, `needs_input` (with questions) or `rejected` (with
     reasons).
   - There is at most one repair round, then an explicit stop.
   - The offline proposer is a scripted fake. A real Claude adapter is strictly opt-in and
     has a spend cap.
7. **Grounded briefs and a named human review.**
   - Briefs are built only from stored ledger records.
   - Every number in a narrative must match a cited stored fact, or the narrative is dropped.
   - A review is recorded in an append-only, hash-chained SQLite ledger. Approval means
     "accepted for discussion"; nothing is deployed.
8. **Pre-registered research studies.** These test the twin against a hidden "truth" simulator
   with mechanisms the twin omits, compare budgeted replication allocation, and assess
   robustness to parameter uncertainty (see [Results](#results)).

Three synthetic domain packs share one interface: **insurance claims**, **procurement
exceptions** and **customer-support escalations**. Each includes an automation option whose
fallout lands on a human queue.

## Prerequisites and quick start (offline, CPU-only)

You need Python 3.11+ and either `uv` or `pip`. No GPU, model download or provider account is
needed.

```bash
uv venv && uv pip install -e ".[dev]"   # or: python -m venv .venv && pip install -e ".[dev]"
# activate: .venv\Scripts\activate (Windows) | source .venv/bin/activate (macOS/Linux)

pytest -q                                  # 72 tests (4 skip without the [llm] extra)
ruff check . && ruff format --check . && mypy src

throughline packs
throughline validate --pack insurance
throughline study --pack insurance --profile quick      # about 1 min; writes results/insurance/
throughline propose --pack insurance "Automate triage under the surge scenario." --run
throughline propose --pack insurance "Skip the fraud check under normal demand."   # rejected
throughline brief --pack insurance                       # grounded draft from the stored study
throughline review --brief <brief-record-id> --reviewer "<name>" --decision approve
throughline ledger verify
```

Full reproduction of every committed result took 9 min 40 s on an Intel i7-11800H (16 logical
CPUs, 16 GB RAM, Windows 11), using 6 worker processes:

```bash
throughline study --pack all --profile full
throughline research --pack all
throughline eval-agent --provider fake
throughline brief --pack insurance   # and procurement, support
throughline dataset --pack insurance --seed 1000   # export a seeded case stream + event log
```

Results are deterministic for a given seed and do not depend on worker count (tested). The
default pool is capped at 6 processes. Set `--workers N` or `THROUGHLINE_WORKERS` to change it.

Local API, unauthenticated and bound to localhost; it uses the scripted proposer only:

```bash
uvicorn throughline.api:app --host 127.0.0.1 --port 8000   # docs at /docs
```

## Opt-in real model (Claude)

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=...           # never committed, never logged or sent in prompts
throughline propose --pack support "Automate routing under normal demand." \
    --provider anthropic --model claude-haiku-5-5 --max-cost-usd 0.05
throughline eval-agent --provider anthropic --model claude-haiku-5-5 --max-cost-usd 0.25
throughline brief --pack support --narrator anthropic --max-cost-usd 0.02
```

- **What is sent.** Only the synthetic pack description (levers, bounds, current values,
  demand conditions, control names) and the request text. For narratives, only stored
  simulation facts are sent.
- **Request settings.** Structured JSON-schema output, `effort: low`, `max_tokens` 2048 and a
  60 s timeout. There is one retry at the HTTP level and at most one repair round.
- **Spend control.** Each call is refused before sending if its worst-case cost would exceed
  the cap (`budget_exhausted`).
- **What is recorded.** The requested and reported model, input and output tokens, latency and
  stop reason, and an estimated cost. Unavailable values are null, not zero.
- **Pricing assumptions** live in [`src/throughline/prices.toml`](src/throughline/prices.toml),
  as of 2026-11-03. Claude Haiku 5.5 is listed at $0.10 / $0.50 per million input / output
  tokens. A proposal prompt is roughly 1–2k input tokens, so all 36 labelled requests should
  cost on the order of $0.01. **This is an estimate. Verify current prices before any run.**
- **Not run yet.** No real-model run has been performed for this repository, so **no
  real-model result is claimed.** The adapter is tested only against a stubbed SDK client
  (`tests/test_anthropic_adapter.py`).

## Architecture

```text
request ─► Proposer (fake | opt-in Claude) ─► schema ─► Critic ─► ChangeSet      [untrusted → trusted]
                                                                   │
OperatingModel ─► levers (capacity | variant | priority) ─► apply_changes ─► validate (controls proved)
                                                                   │
counter-based inputs (digest) ─► SimPy engine (finite resources, horizon, open work) ─► metrics
                                                                   │
replications ─► t-CIs, verified paired / Welch diffs ─► baseline ladder ─► search split ─► held-out
                                                                   │
                     hash-chained ledger ─► grounded brief ─► named review (no deployment)
```

More detail is in [docs/architecture.md](docs/architecture.md). The design decisions are in
[docs/adr](docs/adr):
- [counter-based inputs with verified pairing](docs/adr/0001-counter-based-exogenous-inputs.md);
- [an explicit state machine instead of LangGraph](docs/adr/0002-explicit-state-machine-not-agent-framework.md);
- [bounded enumeration instead of OR-Tools](docs/adr/0003-bounded-enumeration-not-solver.md).

Domain vocabulary is defined in [CONTEXT.md](CONTEXT.md).

## Results

All numbers below come from the committed files in [`results/`](results/), produced by the
commands above. They are simulated outcomes on synthetic packs.

The search split uses seeds 1000–1009 under normal demand. The held-out split uses seeds
9000–9019 under three conditions: normal, +25% surge, and a shifted mix. Intervals are 95%
intervals across replications. Seeds and splits are documented in
[docs/data-and-splits.md](docs/data-and-splits.md).

### 1. Decision studies: the baseline ladder

The objective is cost per case including an SLA-miss penalty. The rule is to minimise it
subject to a mean completion rate of at least 95% and mean SLA attainment of at least 85%.

| Pack | Capacity-aware choice | Held-out normal: Δ objective vs baseline (paired) | Uncapacitated-simulation choice on held-out normal |
|---|---|---|---|
| Insurance | automate triage + high-value-first | −19.20 (−19.46 to −18.94); p95 7.37 → 5.82 h; meets rule | also cuts an adjuster: SLA 89.8%, p95 22.2 h, **fails** rule |
| Procurement | 2 AP clerks + ML-assisted classification | −6.47 (−6.59 to −6.36); meets rule | 2 AP clerks, manual: SLA 5.7%, p95 68.0 h, **fails** rule |
| Support | tier-1 = 3, tier-2 = 6, automated routing | −9.06 (−9.20 to −8.92); meets rule | also cuts a specialist: SLA 27.6%, p95 31.0 h, **fails** rule |

The headline findings:
- **Ignoring contention is the costly mistake.** In all three packs, the uncapacitated
  simulation chose a cheaper configuration that fails the service constraints on held-out
  seeds.
- **A careful spreadsheet was a strong baseline here.** Average-duration arithmetic with an
  offered-load check picked the same configuration as the capacity-aware simulation in
  procurement and support. In insurance it picked the same lever change without the priority
  rule, with an identical objective. We report this rather than presenting it as a win for
  simulation.
- **A downstream shift appears where the model produces it.** In insurance, automating triage
  alone raised adjuster utilisation by 8.0 points, the flagged downstream load increase, while
  still lowering the objective (−18.67, paired).
- **Choices tuned for normal demand break under the held-out surge.** Procurement's choice is
  worse than baseline under +25% demand: +4.72 objective, SLA 34.7% against 74.7%. Support's
  choice drops to 9.3% SLA against the baseline's 72.5%. Under the surge, no evaluated
  insurance alternative meets the rule. The search split did not reveal any of this; the
  held-out evaluation did.

Every pairing claim was verified. Same-condition comparisons had all arrival digests
identical. Cross-condition comparisons (normal against surge) were detected as unpaired and
used Welch intervals. Full tables, Pareto sets and sensitivity analyses are in
`results/<pack>/study-full.md`, and grounded briefs are in `results/<pack>/brief.md`.

### 2. Pre-registered research studies ([docs/preregistration.md](docs/preregistration.md))

The pre-registration was hashed into the ledger before the run; its SHA-256 begins
`fd87abe665fdf5da`. The hidden truth adds three things the twin does not model: handoff
delays, per-shift absenteeism, and a daily arrival peak. The twin is calibrated only from a
960-hour baseline history that the truth produced. Full report:
[results/research.md](results/research.md).

| | Insurance | Procurement | Support |
|---|---|---|---|
| Baseline fit: completion rate, relative error | +3.3% | +2.0% | +3.3% |
| Baseline fit: median cycle time, relative error | −65% | −75% | −82% |
| Baseline fit: SLA attainment, twin vs truth | 98.2% vs 80.6% | 98.7% vs 72.1% | 99.3% vs 57.9% |
| Residual diagnostics flagged (handoff gap, idle capacity while queued, peak-to-trough arrivals) | 3 / 3 | 3 / 3 | 3 / 3 |
| **H1** Kendall τ vs truth (normal / surge): twin | 0.91 / 0.67 | 0.97 / 0.79 | 0.73 / 0.58 |
| **H1** same, spreadsheet and uncapacitated (identical here) | 0.59 / 0.15 | 0.75 / 0.63 | 0.58 / 0.79 |
| **H1** supported? | yes | yes | **no** (worse under surge) |
| **H2** OCBA beats equal allocation (PCS) | no: identical | no: identical | no: identical |
| **H3** robust ≤ point-estimate regret | yes* | yes* (same choice) | **no** |

**"Calibrated but wrong" is the central result.** The calibrated twin reproduces the observed
completion rate within about 3%. It still underestimates median cycle time by 65–82% and
reports roughly 98% SLA attainment where the truth gives 58–81%. All three residual
diagnostics flag the omitted mechanisms from the baseline log alone. A good baseline fit is
not evidence that a twin is accurate under intervention.

H1 ranking validity held in 2 of 3 packs. In support under surge, the simpler baselines
ranked alternatives better than the twin did.

**H2 was uninformative.** In each pack, the best two shortlisted alternatives fell within the
indifference zone, so both procedures reached a probability of correct selection (PCS) of
0.95–1.00 at every budget. The test needs a harder shortlist.

**\*H3 is weak evidence.** Under the truth's surge, *neither* choice met the decision rule in
any pack, so H3 was judged on the truth objective alone. In procurement both methods picked
the same alternative. In support the minimax-regret choice was worse (94.36 against 86.26).
The robustness analysis did flag support's point-estimate choice as fragile: it was feasible
in fewer than 80% of the bootstrap worlds.

With three packs, all of this is descriptive. The hidden truth is another simulator by the
same authors, so these results say nothing about real operations.

### 3. Scenario-proposal evaluation (scripted fake only)

[results/agent/eval-fake.md](results/agent/eval-fake.md) reports **35/36** end-to-end matches:
18/18 on dev requests and 17/18 on held-out. The miss was "reduce specialists by 1", which
the rules did not parse, so only the priority change was proposed.

**This is not AI performance.** The fake is a set of hand-written keyword rules by the same
authors as the requests. The meaningful property is enforced by the critic, independently of
any proposer: **0 of 6 control-removal requests produced a runnable scenario.** Missing values
became questions, and contradictions, out-of-bounds values, over-budget requests and
out-of-scope requests (for example, deploying to production) were rejected with reasons.

## Implemented vs not implemented

| Implemented and tested | Not implemented (gaps) |
|---|---|
| Typed contracts; validator; control-path proofs; human-only controls | Live data ingestion, calibration pipelines for real logs, freshness checks |
| SimPy engine; zero capacity; overload; open-work accounting; Little's law, M/M/c, deterministic tests | Shifts and calendars, abandonment, preemption, batching, load-dependent automation error |
| Counter-based inputs; digest-verified pairing; t / Welch intervals | Variance-reduction beyond common random numbers; warm-up detection |
| Spreadsheet and uncapacitated baselines; bounded enumeration; Pareto set; held-out split; sensitivity | OR-Tools sub-problems; search over spaces larger than 200 combinations; sequential stopping in the main study |
| Three packs on one interface; seeded dataset export | Real or licensed public datasets; validation against observed data |
| Untrusted proposal loop; scripted fake; opt-in Claude adapter (stub-tested); grounded briefs | Any measured real-model result; LangGraph; React UI |
| Append-only, hash-chained ledger; named (self-asserted) review; local API | Authentication, authorisation, signed reviews, PostgreSQL, multi-user operation |
| Hidden-truth validation, OCBA comparison, bootstrap robustness (pre-registered) | Multiple hidden-truth families; more packs; significance testing across packs |

## Trade-offs worth knowing

- **Enumeration instead of an optimiser.** It is exhaustive, auditable and capped, but it only
  works for small spaces.
- **Rules on means, not interval bounds.** This is simpler, but marginal choices can flip
  between replication sets. The held-out split and the robustness study exist to expose this.
- **The economic objective.** Spreading staffed cost over arrivals means higher demand can
  *lower* cost per case while service collapses. That is why the rule has explicit service
  constraints.
- **A deterministic critic over a model.** Safety properties do not depend on proposer
  quality, but legitimate phrasing the proposer misses becomes a question or a rejection, not
  a guess.
- **Calibration uses only the active variants.** An automation never used in history keeps its
  authored parameters, and this is listed in the calibrated model's assumptions.

Full definitions and limitations are in
[docs/assumptions-and-limitations.md](docs/assumptions-and-limitations.md).

## Development history relevant to the results

- Quick pilot runs of the research studies were made during development with the same
  pre-registration.
- The first full run crashed: 16 worker processes exhausted the Windows paging file. Workers
  now load SciPy lazily and the default pool is capped at 6.
- A second full run exposed a labelling bug. Equivalent configurations sometimes collapsed onto
  a larger change set than necessary, which hid the automation-only analysis in insurance.
  This was fixed with a regression test and the full pipeline was re-run. The committed results
  are from that run.
- No mechanism, alternative set or decision rule was tuned after seeing any result.

## License

MIT. See [LICENSE](LICENSE).
