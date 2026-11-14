# Decision study: Procurement exceptions

Model `procurement-exceptions` v1.0.0 (digest `10a877ecc548dcd1`), generator `packs-v1`, exogenous scheme `blake2b-counter-v1`, profile `full`. 1880 simulated replications in 56.1 s.

Search split: seeds 1000–1009 (10), conditions ['normal']. Held-out split: seeds 9000–9019 (20), conditions ['normal', 'surge_25', 'receipt_heavy'].

Decision rule (declared before search): minimise `objective_cost_per_case` subject to mean completion rate >= 0.95 and mean SLA attainment >= 0.85.

Enumerated 72 lever combinations: 70 evaluated, 2 rejected (budget, bounds or controls), 0 behaviourally equivalent duplicates skipped.

## Selections by method (search split)

| Method | Selected alternative | Objective on search split (capacity-aware, 95% CI) |
|---|---|---|
| spreadsheet | capacity:ap_clerk=2, variant:classify=ml_assisted | 117.42 (114.44–120.39) |
| uncapacitated_sim | capacity:ap_clerk=2 | 135.63 (132.43–138.83) |
| capacity_aware_sim | capacity:ap_clerk=2, variant:classify=ml_assisted | 117.42 (114.44–120.39) |

## Held-out evaluation (capacity-aware simulation)

Mean (95% CI) across held-out replications. Differences are versus baseline under the same condition; `paired` only where arrival-stream digests were verified identical.

| Condition | Alternative | Roles | Objective | p95 h (completed) | Completion | SLA | Open | Δ objective vs baseline | Rule |
|---|---|---|---|---|---|---|---|---|---|
| normal | baseline | baseline, pareto | 123.66 (121.97–125.36) | 7.03 (6.46–7.60) | 98.7% (98.3–99.0) | 98.6% (98.2–98.9) | 11.1 (8.1–14.1) | — | meets |
| normal | capacity:ap_clerk=2, variant:classify=ml_assisted | selected:spreadsheet, selected:capacity_aware_sim, pareto | 117.19 (115.59–118.78) | 7.62 (7.00–8.23) | 98.7% (98.3–99.1) | 98.6% (98.1–99.0) | 11.2 (7.8–14.6) | -6.47 (-6.59 to -6.36) paired, alternative | meets |
| normal | capacity:ap_clerk=2 | selected:uncapacitated_sim | 135.58 (133.77–137.40) | 67.99 (63.10–72.89) | 75.0% (73.4–76.7) | 5.7% (3.3–8.2) | 209.5 (193.0–226.0) | +11.92 (+11.32 to +12.53) paired, reference | fails |
| normal | variant:classify=ml_assisted | pareto | 127.81 (126.04–129.57) | 6.14 (5.63–6.66) | 99.1% (98.7–99.4) | 99.0% (98.7–99.3) | 8.0 (5.2–10.8) | +4.14 (+4.06 to +4.23) paired, reference | meets |
| surge_25 | baseline | baseline, pareto | 105.78 (103.84–107.72) | 21.93 (17.81–26.06) | 95.2% (94.2–96.1) | 74.7% (65.6–83.9) | 50.9 (40.3–61.4) | — | fails |
| surge_25 | capacity:ap_clerk=2, variant:classify=ml_assisted | selected:spreadsheet, selected:capacity_aware_sim, pareto | 110.50 (107.93–113.06) | 38.34 (32.82–43.85) | 89.2% (87.6–90.8) | 34.7% (23.3–46.2) | 113.4 (95.5–131.3) | +4.72 (+1.95 to +7.48) paired, reference | fails |
| surge_25 | capacity:ap_clerk=2 | selected:uncapacitated_sim | 114.72 (113.60–115.84) | 134.64 (130.88–138.40) | 49.8% (48.6–50.9) | 0.0% (0.0–0.0) | 524.3 (507.6–541.0) | +8.94 (+6.72 to +11.16) paired, reference | fails |
| surge_25 | variant:classify=ml_assisted | pareto | 106.23 (104.27–108.19) | 17.10 (13.38–20.81) | 97.0% (96.2–97.9) | 86.9% (79.6–94.1) | 31.2 (22.1–40.3) | +0.45 (-1.49 to +2.39) paired, inconclusive | meets |
| receipt_heavy | baseline | baseline, pareto | 120.00 (118.55–121.46) | 7.60 (6.88–8.32) | 98.7% (98.5–98.9) | 98.4% (98.1–98.7) | 11.6 (9.6–13.5) | — | meets |
| receipt_heavy | capacity:ap_clerk=2, variant:classify=ml_assisted | selected:spreadsheet, selected:capacity_aware_sim, pareto | 113.79 (112.42–115.15) | 8.38 (7.61–9.15) | 98.3% (98.0–98.7) | 98.2% (97.8–98.5) | 14.3 (11.3–17.4) | -6.22 (-6.34 to -6.10) paired, alternative | meets |
| receipt_heavy | capacity:ap_clerk=2 | selected:uncapacitated_sim | 132.91 (131.42–134.41) | 77.86 (73.36–82.35) | 71.3% (69.7–73.0) | 2.5% (1.4–3.7) | 247.8 (231.3–264.4) | +12.91 (+12.62 to +13.20) paired, reference | fails |
| receipt_heavy | variant:classify=ml_assisted | pareto | 124.03 (122.50–125.57) | 6.27 (5.76–6.77) | 98.8% (98.6–99.1) | 98.8% (98.5–99.0) | 10.0 (8.0–12.0) | +4.03 (+3.91 to +4.14) paired, reference | meets |

## Automation-only changes (search split)

Change in mean utilisation by resource when only the automation variant is switched on. A rise of at least 5 points is flagged as a downstream load increase.

- `variant:classify=ml_assisted`: utilisation changes ap_clerk -21.0 pts, buyer -1.2 pts, receiving_clerk +1.3 pts; flagged: none; objective difference +4.20 (paired, reference); p95 difference -1.06 h (alternative).

## Sensitivity (held-out seeds, first held-out condition)

| Parameter | Value | Alternative | Objective | SLA | Rule | Δ objective vs baseline |
|---|---|---|---|---|---|---|
| arrival_rate | 0.8 | baseline | 153.05 (150.70–155.40) | 99.1% (98.9–99.4) | meets | — |
| arrival_rate | 0.8 | alt-2-3-1-ml_assisted-fifo | 144.92 (142.70–147.14) | 99.1% (98.9–99.3) | meets | -8.13 (alternative) |
| arrival_rate | 1.2 | baseline | 106.40 (105.10–107.69) | 87.2% (81.1–93.4) | meets | — |
| arrival_rate | 1.2 | alt-2-3-1-ml_assisted-fifo | 107.53 (105.36–109.70) | 61.0% (50.0–72.0) | fails | +1.13 (inconclusive) |
| buyer_service_time | 0.8 | baseline | 123.57 (121.85–125.28) | 99.0% (98.7–99.2) | meets | — |
| buyer_service_time | 0.8 | alt-2-3-1-ml_assisted-fifo | 117.09 (115.47–118.71) | 98.9% (98.6–99.3) | meets | -6.47 (alternative) |
| buyer_service_time | 1.2 | baseline | 126.21 (124.51–127.91) | 88.2% (81.6–94.8) | meets | — |
| buyer_service_time | 1.2 | alt-2-3-1-ml_assisted-fifo | 119.28 (117.79–120.77) | 90.0% (84.1–96.0) | meets | -6.93 (alternative) |
| classify_fallout | 0.15 | baseline | 123.66 (121.97–125.36) | 98.6% (98.2–98.9) | meets | — |
| classify_fallout | 0.15 | alt-2-3-1-ml_assisted-fifo | 117.13 (115.55–118.72) | 98.6% (98.2–99.0) | meets | -6.53 (alternative) |
| classify_fallout | 0.35 | baseline | 123.66 (121.97–125.36) | 98.6% (98.2–98.9) | meets | — |
| classify_fallout | 0.35 | alt-2-3-1-ml_assisted-fifo | 117.51 (115.97–119.05) | 97.5% (96.1–98.9) | meets | -6.15 (alternative) |

## Pairing verification

- search alt-3-3-1-ml_assisted-fifo vs baseline: all 10 arrival-stream digests verified identical
- held-out normal alt-2-3-1-ml_assisted-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-2-3-1-manual-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out normal alt-3-3-1-ml_assisted-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out surge_25 alt-2-3-1-ml_assisted-fifo vs baseline: all 20 arrival-stream digests verified identical
- held-out surge_25 alt-2-3-1-manual-fifo vs baseline: all 20 arrival-stream digests verified identical
- ... 5 more checks in study.json

## Interpretation limits

- Simulated counterfactuals are conditional on this synthetic model; they are not causal estimates or forecasts.
- The capacity-aware selection is re-evaluated on held-out seeds and demand, but the alternative set and decision rule were authored with knowledge of the model.
- Spreadsheet and uncapacitated choices are scored here by the capacity-aware simulation, which is itself only a model.

Ledger record: `experiment-538947a93051`
