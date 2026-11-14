# Results

Every number on this page comes from the committed
[`results/`](https://github.com/bernardosaab/agentic-ops-twin/tree/main/results) directory,
produced by `make reproduce`. The results are simulated on synthetic packs. Intervals are 95%
intervals across independent replications.

| Split | Seeds | Demand conditions |
|---|---|---|
| Search | 1000–1009 | normal |
| Held-out | 9000–9019 | normal, +25% surge, and a pack-specific mix |

## Decision quality: the baseline ladder

![Decision quality](assets/figures/decision-quality-light.svg#only-light)
![Decision quality](assets/figures/decision-quality-dark.svg#only-dark)

| Pack | Capacity-aware choice | Held-out Δ cost per case vs current (paired) | Uncapacitated choice, held-out |
|---|---|---|---|
| Insurance claims | automate triage, high-value-first queue | −19.20 (−19.46 to −18.94); meets the rule | also cuts an adjuster: SLA 89.8%; **fails** |
| Procurement exceptions | 2 AP clerks, ML-assisted classification | −6.47 (−6.59 to −6.36); meets the rule | 2 AP clerks, manual: SLA 5.7%; **fails** |
| Customer support | tier 1 = 3, tier 2 = 6, automated routing | −9.06 (−9.20 to −8.92); meets the rule | also cuts a specialist: SLA 27.6%; **fails** |

- **The uncapacitated simulation fails.** Ignoring contention selected options that fail the
  service rule in every pack.
- **The spreadsheet is a strong baseline.** Average-duration arithmetic with an offered-load
  check matched the capacity-aware choice in two packs. In the third it matched the objective.

## Backlog under a surge

![Backlog under surge](assets/figures/backlog-surge-light.svg#only-light)
![Backlog under surge](assets/figures/backlog-surge-dark.svg#only-dark)

Under +25% demand, no method's choice meets the decision rule in any pack. Two choices are
worse than the current operation:

- **Procurement:** cost per case is 4.72 higher, and SLA attainment is 34.7% against 74.7%.
- **Support:** SLA attainment is 9.3% against 72.5%.

## Downstream shift from automation

![Downstream shift](assets/figures/downstream-shift-light.svg#only-light)
![Downstream shift](assets/figures/downstream-shift-dark.svg#only-dark)

## Hidden-truth validation (pre-registered)

![Calibrated but wrong](assets/figures/calibrated-but-wrong-light.svg#only-light)
![Calibrated but wrong](assets/figures/calibrated-but-wrong-dark.svg#only-dark)

![Ranking validity](assets/figures/ranking-validity-light.svg#only-light)
![Ranking validity](assets/figures/ranking-validity-dark.svg#only-dark)

| Hypothesis | Insurance | Procurement | Support |
|---|---|---|---|
| H1: ranking validity | supported | supported | not supported |
| H2: OCBA beats equal allocation | uninformative (identical) | uninformative (identical) | uninformative (identical) |
| H3: robust choice no worse than the point estimate | supported (weak) | supported (same choice) | not supported |

- **H1:** the twin ranked alternatives closer to the truth than both baselines in insurance
  and procurement, but not in support under the surge.
- **H2:** the top shortlisted alternatives fell within the indifference zone, so the test could
  not separate the two procedures.
- **H3:** no choice met the rule in the truth under the surge, so H3 was judged on the
  objective alone.

The full report is
[results/research.md](https://github.com/bernardosaab/agentic-ops-twin/blob/main/results/research.md).
With three packs, these outcomes are descriptive.
