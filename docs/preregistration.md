# Pre-registration: research studies (v1)

Written before running the research studies. `throughline research` hashes this file (SHA-256)
into the evidence ledger before it runs anything, and the results report quotes that hash. If
this file changes, the hash changes and earlier results no longer match it.

## Setting

All three synthetic packs (insurance, procurement, support). For each pack, a **hidden truth**
simulator is the pack model plus mechanisms the twin does not model:

- handoff delays between steps;
- per-shift absenteeism that removes servers;
- a daily arrival-rate profile, where the twin assumes stationary arrivals.

The twin never sees the hidden truth's parameters. It is calibrated only from an "observed"
baseline history that the hidden truth produced: one 960-hour run with seed 500. This seed is
disjoint from the search seeds (1000–1009), the held-out seeds (9000–9019) and the validation
seeds (7000–7007).

Shared assumption, disclosed: the truth and the twin use the same routing structure, the same
step set, and the same authored parameters for any automation variant that is absent from the
history. A variant that was never used cannot be calibrated from that history.

## Hypotheses and decision rules

**H1: ranking validity.** Across the evaluated alternatives in each pack, the capacity-aware
twin's objective ranking agrees with the hidden truth better than the two baselines do. The
baselines are the spreadsheet (average-duration) estimate and the uncapacitated simulation,
both built from the same calibrated parameters.

- Metric: Kendall τ between each method's predicted `objective_cost_per_case` and the truth's,
  on validation seeds under normal and +25% demand.
- Secondary metrics: whether each method's top choice is also the truth's best feasible
  alternative, and the truth-measured regret of each method's choice.
- Supported in a pack if the twin's τ is higher than both baselines' τ in both demand conditions.

**H2: budgeted selection.** OCBA-style sequential allocation reaches a probability of correct
selection (PCS) at least as high as equal allocation at every tested budget, and strictly higher
at one or more budgets.

- Setup: on the twin itself, the 10 feasible alternatives with the lowest
  spreadsheet-estimated objective. This is a cheap, simulation-free shortlist.
- Correct selection: the choice's long-run mean (60 independent replications) is within δ = 1.0
  currency unit of the best long-run mean.
- Procedure: 400 macro-replications, resampling from a pool of 40 replications per alternative.
- Budgets: 50, 100, 150, 200 total replications.

**H3: robustness.** Under held-out +25% demand in the hidden truth, the minimax-regret choice has
truth regret no greater than the point-estimate choice. This is evaluated per pack.

- Point-estimate choice: the decision rule applied to the calibrated twin under normal demand.
- Minimax-regret choice: among alternatives feasible in at least 80% of worlds, the one with
  the smallest maximum regret.

- The minimax-regret choice is computed across 12 bootstrap-calibrated parameter worlds, with
  4 replications each.
- Ties count as "no difference". With 3 packs, this is descriptive evidence, not a significance
  test.

## Reporting commitments

- Report every pack and every hypothesis, including negative and inconclusive outcomes.
- Report the residual diagnostics, meaning the signals of model inadequacy that the baseline log
  shows, alongside fit.
- Do not tune mechanisms, alternatives or rules after seeing results without bumping this file's
  version and re-running.
