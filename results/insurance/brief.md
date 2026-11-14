# Decision brief (draft): capacity-aware selection `variant:triage=automated, priority:queue_policy=high_value_first`

**Status:** draft for named human review. Approval records a decision for discussion only; nothing is deployed.

- Pack: `insurance`; model `insurance-claims` v1.0.0, digest `09db5f2dd908b6d4`
- Evidence: ledger record `experiment-9029496dc044`
- Narrative source: template-v1; grounding check: passed

## Summary

Under the `normal` condition, cost per case incl. SLA penalty is 165.47 [F2] versus 184.67 [F1] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, cost per completed case is 165.21 [F7] versus 184.53 [F6] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, median cycle time (completed) is 2.21 [F12] versus 3.43 [F11] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, p95 cycle time (completed) is 5.82 [F17] versus 7.37 [F16] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `normal` condition, completion rate is 99.0% [F22] versus 98.5% [F21] for the baseline, higher than the baseline (an improvement); paired comparison. Under the `normal` condition, SLA attainment (open = miss) is 99.0% [F27] versus 98.5% [F26] for the baseline, higher than the baseline (an improvement); paired comparison. Under the `surge_25` condition, cost per case incl. SLA penalty is 141.89 [F42] versus 166.02 [F41] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `surge_25` condition, cost per completed case is 141.22 [F47] versus 164.64 [F46] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `surge_25` condition, median cycle time (completed) is 13.54 [F52] versus 22.15 [F51] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `surge_25` condition, p95 cycle time (completed) is 33.13 [F57] versus 35.80 [F56] for the baseline, with no clear difference from the baseline; paired comparison. Under the `surge_25` condition, completion rate is 91.9% [F62] versus 87.1% [F61] for the baseline, higher than the baseline (an improvement); paired comparison. Under the `surge_25` condition, SLA attainment (open = miss) is 76.8% [F67] versus 53.8% [F66] for the baseline, higher than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, cost per case incl. SLA penalty is 165.63 [F82] versus 184.86 [F81] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, cost per completed case is 165.33 [F87] versus 184.65 [F86] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, median cycle time (completed) is 2.40 [F92] versus 3.60 [F91] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, p95 cycle time (completed) is 6.34 [F97] versus 8.06 [F96] for the baseline, lower than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, completion rate is 99.0% [F102] versus 98.5% [F101] for the baseline, higher than the baseline (an improvement); paired comparison. Under the `complex_mix` condition, SLA attainment (open = miss) is 99.0% [F107] versus 98.5% [F106] for the baseline, higher than the baseline (an improvement); paired comparison. These are simulated outcomes conditional on the stated assumptions.

## Evidence table

| Condition | Metric | Baseline | Alternative | Difference (95% CI) | Method | Verdict |
|---|---|---|---|---|---|---|
| normal | cost per case incl. SLA penalty | 184.67 | 165.47 | -19.20 (-19.46 to -18.94) | paired | alternative |
| normal | cost per completed case | 184.53 | 165.21 | -19.31 (-19.81 to -18.81) | paired | alternative |
| normal | median cycle time (completed) | 3.43 | 2.21 | -1.22 (-1.63 to -0.81) | paired | alternative |
| normal | p95 cycle time (completed) | 7.37 | 5.82 | -1.55 (-2.50 to -0.61) | paired | alternative |
| normal | completion rate | 98.5% | 99.0% | +0.5 pts (+0.1 pts to +0.9 pts) | paired | alternative |
| normal | SLA attainment (open = miss) | 98.5% | 99.0% | +0.5 pts (+0.1 pts to +0.9 pts) | paired | alternative |
| normal | open cases at horizon | 14.8 | 9.7 | -5.05 (-9.00 to -1.10) | paired | alternative |
| normal | manual escalations | 0.0 | 222.2 | +222.15 (+217.49 to +226.81) | paired | reference |
| surge_25 | cost per case incl. SLA penalty | 166.02 | 141.89 | -24.13 (-26.64 to -21.62) | paired | alternative |
| surge_25 | cost per completed case | 164.64 | 141.22 | -23.43 (-25.26 to -21.59) | paired | alternative |
| surge_25 | median cycle time (completed) | 22.15 | 13.54 | -8.61 (-10.43 to -6.79) | paired | alternative |
| surge_25 | p95 cycle time (completed) | 35.80 | 33.13 | -2.67 (-7.07 to +1.74) | paired | inconclusive |
| surge_25 | completion rate | 87.1% | 91.9% | +4.8 pts (+3.7 pts to +6.0 pts) | paired | alternative |
| surge_25 | SLA attainment (open = miss) | 53.8% | 76.8% | +22.9 pts (+16.3 pts to +29.6 pts) | paired | alternative |
| surge_25 | open cases at horizon | 163.3 | 102.2 | -61.10 (-76.11 to -46.09) | paired | alternative |
| surge_25 | manual escalations | 0.0 | 278.4 | +278.35 (+271.88 to +284.82) | paired | reference |
| complex_mix | cost per case incl. SLA penalty | 184.86 | 165.63 | -19.23 (-19.52 to -18.95) | paired | alternative |
| complex_mix | cost per completed case | 184.65 | 165.33 | -19.32 (-20.07 to -18.58) | paired | alternative |
| complex_mix | median cycle time (completed) | 3.60 | 2.40 | -1.20 (-1.55 to -0.85) | paired | alternative |
| complex_mix | p95 cycle time (completed) | 8.06 | 6.34 | -1.72 (-2.63 to -0.81) | paired | alternative |
| complex_mix | completion rate | 98.5% | 99.0% | +0.6 pts (+0.1 pts to +1.0 pts) | paired | alternative |
| complex_mix | SLA attainment (open = miss) | 98.5% | 99.0% | +0.6 pts (+0.1 pts to +1.0 pts) | paired | alternative |
| complex_mix | open cases at horizon | 15.6 | 9.6 | -6.00 (-10.87 to -1.13) | paired | alternative |
| complex_mix | manual escalations | 0.0 | 220.9 | +220.90 (+216.06 to +225.74) | paired | reference |

## What breaks when the demand assumption is wrong

| Option | Demand headroom (rule still met) | First failing level | Binding constraint | Breaks first at |
|---|---|---|---|---|
| current operation | +12% | +14% | mean completion rate 0.948 < 0.95 | triage_officer |
| variant:triage=automated, priority:queue_policy=high_value_first | +19% | +20% | mean completion rate 0.947 < 0.95 | adjuster |

## Constraint checks

- normal: meets the decision rule (meets completion and SLA constraints on the mean)
- surge_25: fails the decision rule (mean completion rate 0.919 < 0.95)
- complex_mix: meets the decision rule (meets completion and SLA constraints on the mean)

## Assumptions

- `ins-a1` (synthetic-hand-authored): Arrivals are stationary Poisson over operating hours; no calendar.
- `ins-a2` (synthetic-hand-authored): Automated triage sends 22% of claims to adjuster review (fallout).
- `ins-a3` (synthetic-hand-authored): 8% of assessments need one more assessment pass (at most two extra).
- `ins-a4` (synthetic-hand-authored): Staff are always available; no absenteeism or handoff delay.
- `ins-a5` (synthetic-hand-authored): SLA miss penalty of 40 per case represents customer and rework cost.

## Limitations

- Results are simulated counterfactuals conditional on the stated operating model and assumptions; they are not causal estimates or forecasts.
- Parameters are synthetic and hand-authored; no real operational data was used or validated.
- Reviewing this brief changes nothing. A change can reach the sandboxed system of record only through a separately staged, approved and verified change package; no live system is connected.

Brief ledger record: `brief-f9376861f947`
