# Decision brief (draft): capacity-aware selection `capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify`

**Status:** draft for named human review. Approval records a decision for discussion only; nothing is deployed.

- Pack: `support`; model `support-escalations` v1.0.0, digest `581d25fe15dde947`
- Evidence: ledger record `experiment-8510b6837cdf`
- Narrative source: template-v1; grounding check: passed

## Summary

Under the `normal` condition, cost per case incl. SLA penalty is 93.78 [F2] versus 102.84 [F1] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, cost per completed case is 93.43 [F7] versus 102.53 [F6] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, median cycle time (completed) is 3.09 [F12] versus 1.96 [F11] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `normal` condition, p95 cycle time (completed) is 7.85 [F17] versus 5.97 [F16] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `normal` condition, completion rate is 98.8% [F22] versus 99.2% [F21] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `normal` condition, SLA attainment (open = miss) is 98.1% [F27] versus 99.1% [F26] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, cost per case incl. SLA penalty is 88.60 [F42] versus 86.70 [F41] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, cost per completed case is 87.38 [F47] versus 84.49 [F46] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, median cycle time (completed) is 28.95 [F52] versus 8.68 [F51] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, p95 cycle time (completed) is 46.86 [F57] versus 17.68 [F56] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, completion rate is 83.0% [F62] versus 95.8% [F61] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `surge_25` condition, SLA attainment (open = miss) is 9.3% [F67] versus 72.5% [F66] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, cost per case incl. SLA penalty is 89.53 [F82] versus 86.13 [F81] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, cost per completed case is 87.48 [F87] versus 85.27 [F86] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, median cycle time (completed) is 25.78 [F92] versus 6.78 [F91] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, p95 cycle time (completed) is 42.65 [F97] versus 15.26 [F96] for the baseline, higher than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, completion rate is 84.6% [F102] versus 96.7% [F101] for the baseline, lower than the baseline (a deterioration); paired comparison. Under the `billing_spike` condition, SLA attainment (open = miss) is 11.0% [F107] versus 84.9% [F106] for the baseline, lower than the baseline (a deterioration); paired comparison. These are simulated outcomes conditional on the stated assumptions.

## Evidence table

| Condition | Metric | Baseline | Alternative | Difference (95% CI) | Method | Verdict |
|---|---|---|---|---|---|---|
| normal | cost per case incl. SLA penalty | 102.84 | 93.78 | -9.06 (-9.20 to -8.92) | paired | alternative |
| normal | cost per completed case | 102.53 | 93.43 | -9.10 (-9.48 to -8.72) | paired | alternative |
| normal | median cycle time (completed) | 1.96 | 3.09 | +1.13 (+0.81 to +1.46) | paired | reference |
| normal | p95 cycle time (completed) | 5.97 | 7.85 | +1.88 (+1.24 to +2.52) | paired | reference |
| normal | completion rate | 99.2% | 98.8% | -0.4 pts (-0.7 pts to -0.1 pts) | paired | reference |
| normal | SLA attainment (open = miss) | 99.1% | 98.1% | -0.9 pts (-1.5 pts to -0.3 pts) | paired | reference |
| normal | open cases at horizon | 15.7 | 23.8 | +8.15 (+2.78 to +13.52) | paired | reference |
| normal | manual escalations | 0.0 | 487.4 | +487.40 (+475.57 to +499.23) | paired | reference |
| surge_25 | cost per case incl. SLA penalty | 86.70 | 88.60 | +1.90 (+0.83 to +2.97) | paired | reference |
| surge_25 | cost per completed case | 84.49 | 87.38 | +2.89 (+2.18 to +3.60) | paired | reference |
| surge_25 | median cycle time (completed) | 8.68 | 28.95 | +20.27 (+18.41 to +22.14) | paired | reference |
| surge_25 | p95 cycle time (completed) | 17.68 | 46.86 | +29.18 (+26.88 to +31.47) | paired | reference |
| surge_25 | completion rate | 95.8% | 83.0% | -12.9 pts (-13.6 pts to -12.1 pts) | paired | reference |
| surge_25 | SLA attainment (open = miss) | 72.5% | 9.3% | -63.2 pts (-70.5 pts to -55.8 pts) | paired | reference |
| surge_25 | open cases at horizon | 102.3 | 417.6 | +315.35 (+296.68 to +334.02) | paired | reference |
| surge_25 | manual escalations | 0.0 | 590.6 | +590.60 (+581.81 to +599.39) | paired | reference |
| billing_spike | cost per case incl. SLA penalty | 86.13 | 89.53 | +3.40 (+2.79 to +4.01) | paired | reference |
| billing_spike | cost per completed case | 85.27 | 87.48 | +2.21 (+1.48 to +2.94) | paired | reference |
| billing_spike | median cycle time (completed) | 6.78 | 25.78 | +19.00 (+17.20 to +20.80) | paired | reference |
| billing_spike | p95 cycle time (completed) | 15.26 | 42.65 | +27.39 (+24.86 to +29.92) | paired | reference |
| billing_spike | completion rate | 96.7% | 84.6% | -12.2 pts (-13.0 pts to -11.3 pts) | paired | reference |
| billing_spike | SLA attainment (open = miss) | 84.9% | 11.0% | -73.9 pts (-78.1 pts to -69.7 pts) | paired | reference |
| billing_spike | open cases at horizon | 79.2 | 372.1 | +292.95 (+272.40 to +313.50) | paired | reference |
| billing_spike | manual escalations | 0.0 | 589.1 | +589.10 (+580.07 to +598.13) | paired | reference |

## What breaks when the demand assumption is wrong

| Option | Demand headroom (rule still met) | First failing level | Binding constraint | Breaks first at |
|---|---|---|---|---|
| current operation | +23% | +25% | mean SLA attainment 0.836 < 0.85 | tier2_agent |
| capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | +8% | +9% | mean SLA attainment 0.829 < 0.85 | tier2_agent |

## Constraint checks

- normal: meets the decision rule (meets completion and SLA constraints on the mean)
- surge_25: fails the decision rule (mean completion rate 0.830 < 0.95)
- billing_spike: fails the decision rule (mean completion rate 0.846 < 0.95)

## Assumptions

- `sup-a1` (synthetic-hand-authored): Ticket value is the refund amount requested.
- `sup-a2` (synthetic-hand-authored): The automated classifier misroutes 25% of tickets; tier 1 fixes them.
- `sup-a3` (synthetic-hand-authored): 30% of tier-2 tickets need a specialist, independent of ticket type.

## Limitations

- Results are simulated counterfactuals conditional on the stated operating model and assumptions; they are not causal estimates or forecasts.
- Parameters are synthetic and hand-authored; no real operational data was used or validated.
- Reviewing this brief changes nothing. A change can reach the sandboxed system of record only through a separately staged, approved and verified change package; no live system is connected.

Brief ledger record: `brief-eacc865a5e61`
