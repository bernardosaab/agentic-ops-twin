# Architecture

```text
 operator request ──► Proposer (scripted fake | opt-in Claude)   UNTRUSTED
                              │ raw JSON
                              ▼
                     parse + Pydantic schema ──► Critic (deterministic)        TRUSTED
                              │                 ok | needs_input | rejected
                              │                 (≤1 repair round, then stop)
                              ▼
 OperatingModel ──► DecisionSpace levers ──► apply_changes ──► validate()      TRUSTED
 (versioned,        (capacity, variant,       (bounds, budget,  (structure +
  digest-bound)      priority only)            control lock)     control paths)
                              │
                              ▼
        counter-based exogenous inputs (seed, stream, case, step, visit)
                              │ arrival-stream digest per replication
                              ▼
          SimPy engine: cases compete for finite resources to a horizon
                              │ ReplicationMetrics (conservation asserted)
                              ▼
   replications ──► t-intervals; paired diffs only if digests match, else Welch
                              │
            baseline ladder: spreadsheet │ uncapacitated │ capacity-aware
                              │
   bounded enumeration ─► decision rule on SEARCH split ─► HELD-OUT re-evaluation
                              │                               + sensitivity
                              ▼
       append-only hash-chained ledger (SQLite) ──► grounded brief ──► named review
                                                     (facts + citations)  (no deployment)
```

## Modules

| Module | Responsibility |
|---|---|
| `core/model.py` | Frozen Pydantic contracts: distributions (inverse-CDF), routing rules, step variants, resources, case types, controls, assumptions; model digest. |
| `core/validate.py` | Assumption critic: references, probabilities, default routes, bounded loops, completion reachability, control-path proofs, human-only controls, zero-capacity warnings. |
| `core/exogenous.py` | BLAKE2b counter-based uniforms, Poisson arrivals (with optional thinning profile), stream digests. |
| `core/engine.py` | SimPy process per case; `PriorityResource` per pool; zero capacity as a never-granted request; horizon cut-off with open-case accounting; hidden mechanisms for validation only. |
| `core/metrics.py`, `core/stats.py` | Metric definitions, Student-t intervals, paired vs Welch differences with pairing verification. |
| `scenarios.py` | Typed levers, bounds, budget, `apply_changes` (re-validates), enumeration with equivalence collapse. |
| `baselines.py` | Spreadsheet average-duration estimate (absorbing-chain visits); uncapacitated mode lives in the engine. |
| `search.py`, `study.py`, `sensitivity.py` | Decision rule, Pareto front, the decision-study pipeline, one-at-a-time sensitivity. |
| `packs/` | Insurance, procurement and support packs behind one `DomainPack` contract; labelled requests. |
| `agent/` | Proposal contracts, scripted fake, opt-in Anthropic adapter, critic, bounded loop, evaluation, grounded brief. |
| `research/` | Calibration from logs, residual diagnostics, OCBA selection, pre-registered studies. |
| `ledger.py` | Append-only (SQLite triggers) and hash-chained evidence records; `verify`. |
| `api.py`, `cli.py` | Local FastAPI service (scripted proposer only) and CLI. |

## Trust boundaries

- **Untrusted:** anything a proposer returns. It is parsed against a strict schema. Values it
  leaves out become operator questions, and its changes can only use declared lever keys.
- **Trusted inputs:** pack models, controls, decision spaces, decision rules and splits. These
  are authored data, versioned and digest-bound.
- **Defence in depth for controls:**
  - No lever type can address routing, controls, costs or demand.
  - The critic rejects any proposed change that names a control.
  - `apply_changes` locks control steps and re-runs the control-path proof.
  - The validator requires control steps to be performed by humans.
  - A test replays event logs to confirm that every simulated case requiring a control
    actually visited it.
- **Not a security boundary.** The API is unauthenticated. Reviewer identity is self-asserted.
  The ledger is tamper-evident only against casual edits.
