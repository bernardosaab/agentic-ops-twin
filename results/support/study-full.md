# Decision study: Customer-support escalations

Model `support-escalations` v1.0.0 (digest `581d25fe15dde947`), generator `packs-v1`, exogenous scheme `blake2b-counter-v1`, profile `full`. 2280 simulated replications in 133.5 s.

Search split: seeds 1000–1009 (10), conditions ['normal']. Held-out split: seeds 9000–9019 (20), conditions ['normal', 'surge_25', 'billing_spike'].

Decision rule (declared before search): minimise `objective_cost_per_case` subject to mean completion rate >= 0.95 and mean SLA attainment >= 0.85.

Enumerated 108 lever combinations: 84 evaluated, 24 rejected (budget, bounds or controls), 0 behaviourally equivalent duplicates skipped.

## Selections by method (search split)

| Method | Selected alternative | Objective on search split (capacity-aware, 95% CI) |
|---|---|---|
| spreadsheet | capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | 93.87 (92.31–95.43) |
| uncapacitated_sim | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3 | 95.24 (92.86–97.62) |
| capacity_aware_sim | capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | 93.87 (92.31–95.43) |

## Held-out evaluation (capacity-aware simulation)

Mean (95% CI) across held-out replications. Differences are versus baseline under the same condition; `paired` only where arrival-stream digests were verified identical.

| Condition | Alternative | Roles | Objective | p95 h (completed) | Completion | SLA | Open | Δ objective vs baseline | Rule |
|---|---|---|---|---|---|---|---|---|---|
| normal | baseline | baseline | 102.84 (101.91–103.78) | 5.97 (5.66–6.28) | 99.2% (99.1–99.3) | 99.1% (98.9–99.2) | 15.7 (12.9–18.4) | — | meets |
| normal | capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | selected:spreadsheet, selected:capacity_aware_sim | 93.78 (92.95–94.61) | 7.85 (7.13–8.58) | 98.8% (98.5–99.1) | 98.1% (97.5–98.8) | 23.8 (18.4–29.2) | -9.06 (-9.20 to -8.92) paired, alternative | meets |
| normal | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3 | selected:uncapacitated_sim | 94.38 (93.32–95.44) | 31.03 (27.23–34.83) | 89.6% (88.3–91.0) | 27.6% (17.7–37.6) | 203.7 (176.2–231.1) | -8.46 (-10.06 to -6.86) paired, alternative | fails |
| normal | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 87.09 (86.36–87.81) | 22.05 (18.73–25.37) | 96.9% (96.3–97.5) | 80.6% (76.9–84.3) | 60.6 (48.9–72.3) | -15.76 (-16.40 to -15.11) paired, alternative | fails |
| normal | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify | pareto | 87.10 (86.38–87.82) | 21.57 (18.35–24.79) | 96.9% (96.3–97.5) | 80.5% (76.6–84.4) | 60.7 (49.0–72.4) | -15.74 (-16.42 to -15.06) paired, alternative | fails |
| normal | capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 91.05 (90.29–91.80) | 21.86 (18.48–25.24) | 97.0% (96.4–97.5) | 80.9% (77.1–84.6) | 59.9 (48.1–71.6) | -11.80 (-12.43 to -11.17) paired, alternative | fails |
| surge_25 | baseline | baseline | 86.70 (85.62–87.77) | 17.68 (15.13–20.23) | 95.8% (95.0–96.7) | 72.5% (64.0–81.0) | 102.3 (81.5–123.1) | — | fails |
| surge_25 | capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | selected:spreadsheet, selected:capacity_aware_sim | 88.60 (87.83–89.36) | 46.86 (43.40–50.32) | 83.0% (81.8–84.1) | 9.3% (6.2–12.5) | 417.6 (387.8–447.5) | +1.90 (+0.83 to +2.97) paired, reference | fails |
| surge_25 | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3 | selected:uncapacitated_sim | 81.70 (81.18–82.23) | 105.85 (102.92–108.78) | 60.6% (59.7–61.5) | 0.0% (0.0–0.0) | 965.2 (938.1–992.3) | -4.99 (-6.22 to -3.77) paired, alternative | fails |
| surge_25 | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 80.84 (80.19–81.49) | 69.51 (65.47–73.55) | 79.9% (78.6–81.1) | 11.1% (8.8–13.4) | 493.3 (460.2–526.4) | -5.86 (-6.94 to -4.79) paired, alternative | fails |
| surge_25 | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify | pareto | 81.37 (80.72–82.03) | 67.45 (63.38–71.52) | 79.9% (78.7–81.1) | 7.5% (5.0–10.0) | 493.1 (461.2–525.0) | -5.32 (-6.37 to -4.27) paired, alternative | fails |
| surge_25 | capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 83.97 (83.28–84.66) | 69.16 (64.93–73.38) | 80.0% (78.7–81.3) | 11.7% (9.1–14.2) | 489.9 (456.6–523.2) | -2.73 (-3.81 to -1.65) paired, alternative | fails |
| billing_spike | baseline | baseline | 86.13 (85.28–86.98) | 15.26 (12.83–17.68) | 96.7% (96.0–97.4) | 84.9% (79.6–90.2) | 79.2 (62.7–95.7) | — | fails |
| billing_spike | capacity:tier1_agent=3, capacity:tier2_agent=6, variant:routing=auto_classify | selected:spreadsheet, selected:capacity_aware_sim | 89.53 (88.73–90.32) | 42.65 (39.51–45.78) | 84.6% (83.4–85.7) | 11.0% (7.4–14.7) | 372.1 (343.4–400.9) | +3.40 (+2.79 to +4.01) paired, reference | fails |
| billing_spike | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3 | selected:uncapacitated_sim | 82.77 (82.30–83.23) | 100.67 (97.81–103.53) | 62.4% (61.4–63.3) | 0.0% (0.0–0.0) | 907.1 (880.2–934.1) | -3.36 (-4.14 to -2.58) paired, alternative | fails |
| billing_spike | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 81.62 (80.97–82.27) | 64.93 (60.33–69.52) | 81.6% (80.3–82.8) | 13.0% (10.3–15.8) | 444.3 (414.0–474.6) | -4.51 (-5.13 to -3.88) paired, alternative | fails |
| billing_spike | capacity:tier1_agent=3, capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify | pareto | 82.23 (81.56–82.89) | 62.59 (58.18–67.01) | 81.4% (80.2–82.7) | 8.9% (6.0–11.9) | 447.1 (417.4–476.8) | -3.90 (-4.51 to -3.28) paired, alternative | fails |
| billing_spike | capacity:tier2_agent=6, capacity:specialist=3, variant:routing=auto_classify, priority:queue_policy=high_value_first | pareto | 84.84 (84.17–85.51) | 64.79 (59.98–69.60) | 81.6% (80.3–82.8) | 13.3% (10.5–16.1) | 443.6 (413.0–474.3) | -1.29 (-1.93 to -0.65) paired, alternative | fails |

## Automation-only changes (search split)

Change in mean utilisation by resource when only the automation variant is switched on. A rise of at least 5 points is flagged as a downstream load increase.

- `variant:routing=auto_classify`: utilisation changes tier1_agent -17.6 pts; flagged: none; objective difference +0.50 (paired, reference); p95 difference -0.31 h (alternative).

## Sensitivity (held-out seeds, first held-out condition)

| Parameter | Value | Alternative | Objective | SLA | Rule | Δ objective vs baseline |
|---|---|---|---|---|---|---|
| arrival_rate | 0.8 | baseline | 127.76 (126.54–128.98) | 99.3% (99.2–99.4) | meets | — |
| arrival_rate | 0.8 | alt-3-6-4-auto_classify-fifo | 116.29 (115.18–117.40) | 99.3% (99.1–99.4) | meets | -11.47 (alternative) |
| arrival_rate | 1.2 | baseline | 87.22 (86.60–87.83) | 91.6% (88.7–94.6) | meets | — |
| arrival_rate | 1.2 | alt-3-6-4-auto_classify-fifo | 90.75 (89.86–91.63) | 15.8% (10.4–21.2) | fails | +3.53 (reference) |
| specialist_service_time | 0.8 | baseline | 102.82 (101.89–103.75) | 99.2% (99.1–99.4) | meets | — |
| specialist_service_time | 0.8 | alt-3-6-4-auto_classify-fifo | 93.72 (92.88–94.55) | 98.6% (98.1–99.0) | meets | -9.11 (alternative) |
| specialist_service_time | 1.2 | baseline | 103.47 (102.52–104.42) | 94.8% (92.6–97.1) | meets | — |
| specialist_service_time | 1.2 | alt-3-6-4-auto_classify-fifo | 94.51 (93.64–95.38) | 93.2% (90.8–95.7) | meets | -8.96 (alternative) |
| misroute_rate | 0.15 | baseline | 102.84 (101.91–103.78) | 99.1% (98.9–99.2) | meets | — |
| misroute_rate | 0.15 | alt-3-6-4-auto_classify-fifo | 93.75 (92.92–94.59) | 98.2% (97.5–98.9) | meets | -9.09 (alternative) |
| misroute_rate | 0.35 | baseline | 102.84 (101.91–103.78) | 99.1% (98.9–99.2) | meets | — |
| misroute_rate | 0.35 | alt-3-6-4-auto_classify-fifo | 93.82 (92.99–94.65) | 98.0% (97.3–98.6) | meets | -9.02 (alternative) |

## Pairing verification

- search alt-4-7-4-auto_classify-fifo vs baseline: all 10 arrival-stream digests verified identical
- held-out normal alt-3-6-4-auto_classify-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-3-6-3-manual-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-3-6-3-auto_classify-high_value_first vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-3-6-3-auto_classify-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-4-6-3-auto_classify-high_value_first vs baseline: all 20 arrival-stream digests verified identical
- ... 11 more checks in study.json

## Interpretation limits

- Simulated counterfactuals are conditional on this synthetic model; they are not causal estimates or forecasts.
- The capacity-aware selection is re-evaluated on held-out seeds and demand, but the alternative set and decision rule were authored with knowledge of the model.
- Spreadsheet and uncapacitated choices are scored here by the capacity-aware simulation, which is itself only a model.

Ledger record: `experiment-38ae1a8c0102`
