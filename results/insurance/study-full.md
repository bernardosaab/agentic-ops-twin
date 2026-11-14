# Decision study: Insurance claims

Model `insurance-claims` v1.0.0 (digest `09db5f2dd908b6d4`), generator `packs-v1`, exogenous scheme `blake2b-counter-v1`, profile `full`. 1580 simulated replications in 61.7 s.

Search split: seeds 1000–1009 (10), conditions ['normal']. Held-out split: seeds 9000–9019 (20), conditions ['normal', 'surge_25', 'complex_mix'].

Decision rule (declared before search): minimise `objective_cost_per_case` subject to mean completion rate >= 0.95 and mean SLA attainment >= 0.85.

Enumerated 96 lever combinations: 52 evaluated, 12 rejected (budget, bounds or controls), 32 behaviourally equivalent duplicates skipped.

## Selections by method (search split)

| Method | Selected alternative | Objective on search split (capacity-aware, 95% CI) |
|---|---|---|
| spreadsheet | variant:triage=automated | 161.72 (158.57–164.87) |
| uncapacitated_sim | capacity:adjuster=5, variant:triage=automated | 150.92 (148.43–153.42) |
| capacity_aware_sim | variant:triage=automated, priority:queue_policy=high_value_first | 161.72 (158.57–164.87) |

## Held-out evaluation (capacity-aware simulation)

Mean (95% CI) across held-out replications. Differences are versus baseline under the same condition; `paired` only where arrival-stream digests were verified identical.

| Condition | Alternative | Roles | Objective | p95 h (completed) | Completion | SLA | Open | Δ objective vs baseline | Rule |
|---|---|---|---|---|---|---|---|---|---|
| normal | baseline | baseline | 184.67 (181.66–187.68) | 7.37 (6.22–8.52) | 98.5% (98.2–98.9) | 98.5% (98.2–98.9) | 14.8 (11.0–18.5) | — | meets |
| normal | variant:triage=automated | selected:spreadsheet | 165.47 (162.71–168.23) | 5.89 (5.38–6.39) | 99.0% (98.9–99.2) | 99.0% (98.9–99.2) | 9.7 (8.3–11.1) | -19.20 (-19.47 to -18.94) paired, alternative | meets |
| normal | capacity:adjuster=5, variant:triage=automated | selected:uncapacitated_sim, pareto | 153.64 (151.47–155.82) | 22.16 (17.86–26.45) | 94.9% (93.5–96.3) | 89.8% (85.5–94.1) | 51.5 (36.8–66.1) | -31.03 (-33.04 to -29.02) paired, alternative | fails |
| normal | variant:triage=automated, priority:queue_policy=high_value_first | selected:capacity_aware_sim, pareto | 165.47 (162.70–168.24) | 5.82 (5.32–6.32) | 99.0% (98.8–99.2) | 99.0% (98.8–99.2) | 9.7 (8.0–11.4) | -19.20 (-19.46 to -18.94) paired, alternative | meets |
| normal | capacity:adjuster=5, variant:triage=automated, priority:queue_policy=high_value_first | pareto | 153.99 (151.73–156.25) | 23.42 (18.62–28.21) | 94.9% (93.5–96.3) | 89.0% (84.3–93.7) | 51.5 (37.1–65.9) | -30.68 (-32.86 to -28.51) paired, alternative | fails |
| surge_25 | baseline | baseline | 166.02 (163.08–168.96) | 35.80 (31.19–40.41) | 87.1% (85.2–88.9) | 53.8% (43.9–63.7) | 163.3 (137.8–188.8) | — | fails |
| surge_25 | variant:triage=automated | selected:spreadsheet | 141.45 (138.76–144.13) | 31.37 (25.91–36.83) | 91.9% (90.3–93.4) | 77.8% (70.5–85.1) | 102.9 (82.2–123.6) | -24.57 (-27.05 to -22.10) paired, alternative | fails |
| surge_25 | capacity:adjuster=5, variant:triage=automated | selected:uncapacitated_sim, pareto | 152.93 (150.95–154.90) | 89.66 (84.70–94.61) | 74.2% (72.6–75.7) | 17.2% (14.0–20.4) | 324.4 (301.7–347.1) | -13.10 (-16.01 to -10.19) paired, alternative | fails |
| surge_25 | variant:triage=automated, priority:queue_policy=high_value_first | selected:capacity_aware_sim, pareto | 141.89 (139.13–144.66) | 33.13 (27.30–38.97) | 91.9% (90.4–93.5) | 76.8% (69.3–84.3) | 102.2 (81.6–122.8) | -24.13 (-26.64 to -21.62) paired, alternative | fails |
| surge_25 | capacity:adjuster=5, variant:triage=automated, priority:queue_policy=high_value_first | pareto | 151.44 (149.48–153.41) | 94.48 (88.87–100.08) | 74.4% (72.8–75.9) | 21.1% (18.3–24.0) | 322.1 (299.8–344.3) | -14.58 (-17.59 to -11.57) paired, alternative | fails |
| complex_mix | baseline | baseline | 184.86 (181.85–187.88) | 8.06 (6.72–9.40) | 98.5% (97.9–99.0) | 98.5% (97.9–99.0) | 15.6 (9.8–21.3) | — | meets |
| complex_mix | variant:triage=automated | selected:spreadsheet | 165.62 (162.86–168.38) | 6.36 (5.74–6.97) | 99.1% (98.9–99.3) | 99.1% (98.9–99.3) | 9.3 (7.5–11.1) | -19.24 (-19.53 to -18.96) paired, alternative | meets |
| complex_mix | capacity:adjuster=5, variant:triage=automated | selected:uncapacitated_sim, pareto | 154.18 (152.10–156.26) | 23.64 (19.02–28.25) | 95.0% (93.5–96.4) | 88.9% (84.1–93.7) | 51.1 (35.9–66.3) | -30.68 (-32.92 to -28.44) paired, alternative | fails |
| complex_mix | variant:triage=automated, priority:queue_policy=high_value_first | selected:capacity_aware_sim, pareto | 165.63 (162.86–168.39) | 6.34 (5.66–7.02) | 99.0% (98.9–99.2) | 99.0% (98.9–99.2) | 9.6 (7.7–11.4) | -19.23 (-19.52 to -18.95) paired, alternative | meets |
| complex_mix | capacity:adjuster=5, variant:triage=automated, priority:queue_policy=high_value_first | pareto | 155.09 (152.61–157.58) | 25.37 (20.31–30.43) | 95.0% (93.6–96.4) | 86.7% (80.4–93.0) | 51.0 (35.9–66.1) | -29.77 (-32.55 to -26.98) paired, alternative | fails |

## Automation-only changes (search split)

Change in mean utilisation by resource when only the automation variant is switched on. A rise of at least 5 points is flagged as a downstream load increase.

- `variant:triage=automated`: utilisation changes adjuster +8.0 pts; flagged: ['adjuster']; objective difference -18.67 (paired, alternative); p95 difference -2.09 h (alternative).

## Sensitivity (held-out seeds, first held-out condition)

| Parameter | Value | Alternative | Objective | SLA | Rule | Δ objective vs baseline |
|---|---|---|---|---|---|---|
| arrival_rate | 0.8 | baseline | 229.92 (225.90–233.95) | 99.0% (98.8–99.2) | meets | — |
| arrival_rate | 0.8 | alt-2-6-1-automated-high_value_first | 206.01 (202.40–209.62) | 99.2% (99.0–99.4) | meets | -23.91 (alternative) |
| arrival_rate | 1.2 | baseline | 162.71 (159.67–165.75) | 76.9% (66.4–87.3) | fails | — |
| arrival_rate | 1.2 | alt-2-6-1-automated-high_value_first | 141.65 (139.61–143.68) | 90.5% (86.4–94.5) | meets | -21.07 (alternative) |
| adjuster_service_time | 0.8 | baseline | 184.62 (181.62–187.62) | 98.7% (98.3–99.0) | meets | — |
| adjuster_service_time | 0.8 | alt-2-6-1-automated-high_value_first | 165.36 (162.62–168.09) | 99.3% (99.2–99.4) | meets | -19.26 (alternative) |
| adjuster_service_time | 1.2 | baseline | 184.91 (181.94–187.87) | 97.9% (97.5–98.4) | meets | — |
| adjuster_service_time | 1.2 | alt-2-6-1-automated-high_value_first | 169.56 (167.07–172.04) | 88.6% (83.7–93.5) | fails | -15.35 (alternative) |
| triage_fallout | 0.12 | baseline | 184.67 (181.66–187.68) | 98.5% (98.2–98.9) | meets | — |
| triage_fallout | 0.12 | alt-2-6-1-automated-high_value_first | 165.34 (162.58–168.10) | 99.1% (98.9–99.3) | meets | -19.33 (alternative) |
| triage_fallout | 0.32 | baseline | 184.67 (181.66–187.68) | 98.5% (98.2–98.9) | meets | — |
| triage_fallout | 0.32 | alt-2-6-1-automated-high_value_first | 165.62 (162.86–168.38) | 98.9% (98.7–99.1) | meets | -19.05 (alternative) |

## Pairing verification

- search alt-2-6-1-automated-fifo vs baseline: all 10 arrival-stream digests verified identical
- held-out normal alt-2-6-1-automated-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-2-5-1-automated-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-2-6-1-automated-high_value_first vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-2-5-1-automated-high_value_first vs baseline: all 20 arrival-stream digests verified identical
- held-out surge_25 alt-2-6-1-automated-fifo vs baseline: all 20 arrival-stream digests verified identical
- ... 8 more checks in study.json

## Interpretation limits

- Simulated counterfactuals are conditional on this synthetic model; they are not causal estimates or forecasts.
- The capacity-aware selection is re-evaluated on held-out seeds and demand, but the alternative set and decision rule were authored with knowledge of the model.
- Spreadsheet and uncapacitated choices are scored here by the capacity-aware simulation, which is itself only a model.

Ledger record: `experiment-7a2d60c97332`
