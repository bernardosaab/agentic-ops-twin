# Decision brief (draft): capacity-aware selection `capacity:ap_clerk=2, variant:classify=ml_assisted`

**Status:** draft for named human review. Approval records a decision for discussion only; nothing is deployed.

- Pack: `procurement`; model `procurement-exceptions` v1.0.0, digest `10a877ecc548dcd1`
- Evidence: ledger record `experiment-00fdcefe3fab`
- Narrative source: template-v1; grounding check: passed

## Summary

Under the `normal` condition, cost per case incl. SLA penalty is 117.19 [F2] versus 123.66 [F1] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, cost per completed case is 117.06 [F7] versus 123.62 [F6] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, median cycle time (completed) is 3.16 [F12] versus 2.85 [F11] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `normal` condition, p95 cycle time (completed) is 7.62 [F17] versus 7.03 [F16] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `normal` condition, completion rate is 98.7% [F22] versus 98.7% [F21] for the baseline, with no clear difference from the baseline; paired comparison. Under the `normal` condition, SLA attainment (open = miss) is 98.6% [F27] versus 98.6% [F26] for the baseline, with no clear difference from the baseline; paired comparison. Under the `surge_25` condition, cost per case incl. SLA penalty is 110.50 [F42] versus 105.78 [F41] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, cost per completed case is 102.86 [F47] versus 102.43 [F46] for the baseline, with no clear difference from the baseline; paired comparison. Under the `surge_25` condition, median cycle time (completed) is 20.13 [F52] versus 10.44 [F51] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, p95 cycle time (completed) is 38.34 [F57] versus 21.93 [F56] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, completion rate is 89.2% [F62] versus 95.2% [F61] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, SLA attainment (open = miss) is 34.7% [F67] versus 74.7% [F66] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `receipt_heavy` condition, cost per case incl. SLA penalty is 113.79 [F82] versus 120.00 [F81] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `receipt_heavy` condition, cost per completed case is 113.80 [F87] versus 119.89 [F86] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `receipt_heavy` condition, median cycle time (completed) is 3.50 [F92] versus 3.11 [F91] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `receipt_heavy` condition, p95 cycle time (completed) is 8.38 [F97] versus 7.60 [F96] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `receipt_heavy` condition, completion rate is 98.3% [F102] versus 98.7% [F101] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `receipt_heavy` condition, SLA attainment (open = miss) is 98.2% [F107] versus 98.4% [F106] for the baseline, with no clear difference from the baseline; paired comparison. These are simulated outcomes conditional on the stated assumptions.

## Evidence table

| Condition | Metric | Baseline | Alternative | Difference (95% CI) | Method | Verdict |
|---|---|---|---|---|---|---|
| normal | cost per case incl. SLA penalty | 123.66 | 117.19 | -6.47 (-6.59 to -6.36) | paired | alternative |
| normal | cost per completed case | 123.62 | 117.06 | -6.56 (-6.87 to -6.24) | paired | alternative |
| normal | median cycle time (completed) | 2.85 | 3.16 | +0.31 (+0.14 to +0.47) | paired | reference |
| normal | p95 cycle time (completed) | 7.03 | 7.62 | +0.59 (+0.10 to +1.07) | paired | reference |
| normal | completion rate | 98.7% | 98.7% | -0.0 pts (-0.2 pts to +0.2 pts) | paired | inconclusive |
| normal | SLA attainment (open = miss) | 98.6% | 98.6% | +0.0 pts (-0.3 pts to +0.3 pts) | paired | inconclusive |
| normal | open cases at horizon | 11.1 | 11.2 | +0.10 (-1.61 to +1.81) | paired | inconclusive |
| normal | manual escalations | 0.0 | 209.9 | +209.95 (+203.34 to +216.56) | paired | reference |
| surge_25 | cost per case incl. SLA penalty | 105.78 | 110.50 | +4.72 (+1.95 to +7.48) | paired | reference |
| surge_25 | cost per completed case | 102.43 | 102.86 | +0.43 (-1.23 to +2.09) | paired | inconclusive |
| surge_25 | median cycle time (completed) | 10.44 | 20.13 | +9.69 (+7.57 to +11.81) | paired | reference |
| surge_25 | p95 cycle time (completed) | 21.93 | 38.34 | +16.40 (+12.30 to +20.51) | paired | reference |
| surge_25 | completion rate | 95.2% | 89.2% | -6.0 pts (-7.4 pts to -4.5 pts) | paired | reference |
| surge_25 | SLA attainment (open = miss) | 74.7% | 34.7% | -40.0 pts (-51.1 pts to -28.9 pts) | paired | reference |
| surge_25 | open cases at horizon | 50.9 | 113.4 | +62.55 (+46.88 to +78.22) | paired | reference |
| surge_25 | manual escalations | 0.0 | 250.8 | +250.80 (+244.00 to +257.60) | paired | reference |
| receipt_heavy | cost per case incl. SLA penalty | 120.00 | 113.79 | -6.22 (-6.34 to -6.10) | paired | alternative |
| receipt_heavy | cost per completed case | 119.89 | 113.80 | -6.10 (-6.40 to -5.79) | paired | alternative |
| receipt_heavy | median cycle time (completed) | 3.11 | 3.50 | +0.39 (+0.20 to +0.58) | paired | reference |
| receipt_heavy | p95 cycle time (completed) | 7.60 | 8.38 | +0.78 (+0.06 to +1.50) | paired | reference |
| receipt_heavy | completion rate | 98.7% | 98.3% | -0.3 pts (-0.6 pts to -0.0 pts) | paired | reference |
| receipt_heavy | SLA attainment (open = miss) | 98.4% | 98.2% | -0.3 pts (-0.6 pts to +0.1 pts) | paired | inconclusive |
| receipt_heavy | open cases at horizon | 11.6 | 14.3 | +2.80 (+0.31 to +5.29) | paired | reference |
| receipt_heavy | manual escalations | 0.0 | 215.4 | +215.40 (+208.73 to +222.07) | paired | reference |

## Constraint checks

- normal: meets the decision rule (meets completion and SLA constraints on the mean)
- surge_25: fails the decision rule (mean completion rate 0.892 < 0.95)
- receipt_heavy: meets the decision rule (meets completion and SLA constraints on the mean)

## Assumptions

- `proc-a1` (synthetic-hand-authored): Case type is not observed by routing; classification splits 67/33.
- `proc-a2` (synthetic-hand-authored): ML-assisted classification sends 25% of exceptions to clerk review.
- `proc-a3` (synthetic-hand-authored): 12% of matches fail back to resolution (max twice), then approval.
- `proc-a4` (synthetic-hand-authored): Supplier response time is folded into buyer service time.

## Limitations

- Results are simulated counterfactuals conditional on the stated operating model and assumptions; they are not causal estimates or forecasts.
- Parameters are synthetic and hand-authored; no real operational data was used or validated.
- Approval of this brief records a decision for discussion only. Nothing is deployed and the prototype has no connection to live systems.

Brief ledger record: `brief-07f49f0e1aba`
