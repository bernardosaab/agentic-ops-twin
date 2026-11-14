# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

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
