# Agentic Ops Twin

**Capacity-aware operating-model simulation with governed, agent-assisted scenario analysis.**

AI can speed up one step of a process while shifting work into another queue. Agentic Ops Twin
simulates individual cases competing for finite people and automation. It compares only
*permitted* operating changes, re-checks every recommendation on held-out data, and keeps
mandatory controls out of reach of any optimiser or AI proposal.

![Decision quality on held-out data](assets/figures/decision-quality-light.svg#only-light)
![Decision quality on held-out data](assets/figures/decision-quality-dark.svg#only-dark)

!!! note "Scope"
    This is an **offline simulation prototype** using synthetic data. It never changes a live
    system. Simulated counterfactuals depend on the stated model. They are not causal estimates
    or forecasts.

## What you get

- **A SimPy engine.**
  - Individual cases, finite pooled resources and a finite horizon.
  - Open work is counted, never dropped.
  - Every input must be stated: missing or inconsistent assumptions are rejected.
- **Mandatory controls.** A proof checks every routing path for every control, and control
  steps must be performed by humans. No lever can reach a control, and every changed model is
  proved again.
- **Statistically honest comparisons.**
  - Repeated replications with 95% intervals.
  - Pairing is verified by arrival-stream digests.
  - The decision rule is declared before the search, and selected options are re-evaluated on
    a held-out split.
- **A baseline ladder.** Three methods are compared: spreadsheet arithmetic, an uncapacitated
  simulation, and the capacity-aware simulation.
- **Untrusted AI proposals.** A deterministic critic validates each proposal and asks questions
  rather than guessing. Briefs are grounded so every number cites a stored result, and each
  brief goes to a named human for review.
- **Pre-registered research.** A hidden-truth validation study, budgeted selection, and
  robustness to parameter uncertainty.

Next: [Getting started](getting-started.md) · [How it works](architecture.md) ·
[Results](results.md)
