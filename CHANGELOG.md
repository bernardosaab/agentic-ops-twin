# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-14

### Added
- **Governed write-back** to a sandboxed system of record:
  - escrowed change packages with a field-level quote, a policy-set risk tier and a payload
    hash;
  - HMAC approval tokens bound to the exact payload;
  - maker-checker approval, with two approvers required for high-risk changes;
  - fail-closed release checks;
  - a read-back check after every write;
  - refusal records.
- **Model trust gate.** The residual diagnostics classify a twin as validated, unvalidated or
  inadequate. An inadequate twin blocks release; an unvalidated twin forces the high-risk
  approval path, with every approver acknowledging the status.
- **Decision provenance graph.** The ledger now has typed edges, valid and transaction time,
  invalidate-not-delete, as-of queries, lineage, and exportable reconstruction packs.
- **Compiled-path-first routing.** Deterministic rules run first and skip with a reason instead
  of guessing. Skipped requests escalate to model tiers or to a human queue, with an optional
  shadow mode.
- **Breaking-point stress tests.** Briefs now report demand headroom and which resource breaks
  first.
- **Harness evaluation.** Golden jobs and negative tests run in isolated workspaces, and the
  routing evaluation reports correct, wrong and skipped counts separately.
- `ops-twin reproduce` runs the whole pipeline on any platform, and a headroom figure was added.

### Changed
- Briefs now carry their change set and stress results. Reviewing a brief changes nothing; only
  a released change package can write to the sandbox.

## [0.1.0] - 2026-11-14

### Added

- **Simulation core**
  - Typed operating-model contracts and a validator, including control-path proofs and
    human-only control steps.
  - SimPy engine with finite resources, a finite horizon, open-work accounting, and
    zero-capacity and overload handling. Hidden-truth mechanisms are used only for validation.
  - Counter-based random inputs, with pairing verified by arrival-stream digests.
- **Decision analysis**
  - Bounded levers, with enumeration that collapses equivalent options.
  - Baseline ladder comparing a spreadsheet, an uncapacitated simulation and the
    capacity-aware simulation.
  - Search and held-out splits, Pareto sets, and one-at-a-time sensitivity.
  - Three synthetic domain packs on one interface: insurance, procurement and support.
- **Agent-assisted proposals**
  - Proposal loop with a deterministic critic and a scripted offline fake.
  - Opt-in Anthropic adapter with a spend cap.
  - 36 labelled requests.
- **Governance**
  - Grounded decision briefs.
  - Append-only, hash-chained ledger with named review records.
- **Research**
  - Pre-registered studies: hidden-truth validation with residual diagnostics, OCBA versus
    equal allocation, and bootstrap robustness.
- **Tooling**
  - CLI (`ops-twin`), local FastAPI service, generated figures, MkDocs site and CI.
