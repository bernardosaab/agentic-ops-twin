# Research studies (pre-registered)

Pre-registration SHA-256 `fd87abe665fdf5da` (ledger record `preregistration-a69a63f1116b`). Profile: full.

| Pack | H1 ranking validity | H2 OCBA ≥ equal | H3 robust ≤ point regret | Runtime s |
|---|---|---|---|---|
| insurance | yes | no | yes | 78.6 |
| procurement | yes | no | yes | 69.1 |
| support | no | no | no | 153.9 |

## insurance

### H1: hidden-truth validation

History: 960 h, 3517 arrivals (seed 500). Hidden mechanisms: Truth adds 0.2h handoff delays, 8% per-shift absenteeism and a daily peak.

Residual diagnostics on the baseline log:

- `mean_handoff_gap_hours` = 0.200 (threshold 1e-06): **flagged**. The twin assumes zero time between steps; a positive gap means unmodelled handoff delay.
- `idle_capacity_while_queued` = 0.629 (threshold 0.05): **flagged**. Share of time work waited although fewer than the nominal servers were busy (worst resource: senior_approver); suggests effective capacity below nominal.
- `peak_to_trough_hourly_arrivals` = 11.111 (threshold 2.0): **flagged**. Ratio of busiest to quietest hour-of-day arrival rate (mean 3.66/h); the twin assumes a constant rate.

Baseline fit under normal demand (twin vs truth):

| Metric | Truth | Twin | Relative error |
|---|---|---|---|
| cycle_median_hours | 14.638 | 5.079 | -0.653 |
| cycle_p95_hours | 23.026 | 9.091 | -0.605 |
| completion_rate | 0.951 | 0.982 | 0.033 |
| sla_attainment | 0.806 | 0.982 | 0.218 |
| objective_cost_per_case | 193.446 | 179.667 | -0.071 |

| Condition | Method | Kendall τ vs truth | Objective MAPE | Choice | Truth regret | Choice feasible in truth |
|---|---|---|---|---|---|---|
| normal | capacity_aware_twin | 0.909 | 0.048 | baseline | n/a | no |
| normal | uncapacitated_sim | 0.585 | 0.092 | alt-1-5-1-manual-high_value_first | n/a | no |
| normal | spreadsheet | 0.585 | 0.090 | baseline | n/a | no |
| normal | truth best feasible | — | — | alt-2-6-2-automated-high_value_first | — | — |
| surge_25 | capacity_aware_twin | 0.667 | 0.055 | alt-2-8-1-automated-high_value_first | 0.00 | yes |
| surge_25 | uncapacitated_sim | 0.154 | 0.147 | alt-1-5-1-manual-high_value_first | n/a | no |
| surge_25 | spreadsheet | 0.154 | 0.150 | alt-3-6-1-manual-high_value_first | n/a | no |
| surge_25 | truth best feasible | — | — | alt-2-8-1-automated-high_value_first | — | — |

Kept at authored values (not observable in history): `triage.automated`, `manual_review.manual (too few observations)`

### H2: budgeted selection (on the twin)

10 alternatives; long-run means from 60 replications; gap best to second 0.00; 2 alternative(s) within δ = 1.0; 400 macro-replications from a pool of 40.

| Budget | PCS equal (±SE) | PCS OCBA (±SE) |
|---|---|---|
| 50 | 0.953 ± 0.011 | 0.953 ± 0.011 |
| 100 | 0.998 ± 0.002 | 0.998 ± 0.002 |
| 150 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 200 | 1.000 ± 0.000 | 1.000 ± 0.000 |

### H3: robustness across bootstrap parameter worlds

12 worlds × 4 replications. Point choice `baseline`; minimax-regret choice `alt-2-5-2-automated-fifo`; point choice fragile (feasible in < 80% of worlds): no.

In the hidden truth under held-out +25% demand:

- point choice: objective 185.22, meets rule no, regret n/a
- robust choice: objective 174.38, meets rule no, regret n/a
- basis for H3: neither choice meets the decision rule in truth; compared on truth objective only


## procurement

### H1: hidden-truth validation

History: 960 h, 2983 arrivals (seed 500). Hidden mechanisms: Truth adds 0.3h handoff delays, 10% per-shift absenteeism and a daily peak.

Residual diagnostics on the baseline log:

- `mean_handoff_gap_hours` = 0.300 (threshold 1e-06): **flagged**. The twin assumes zero time between steps; a positive gap means unmodelled handoff delay.
- `idle_capacity_while_queued` = 0.741 (threshold 0.05): **flagged**. Share of time work waited although fewer than the nominal servers were busy (worst resource: finance_approver); suggests effective capacity below nominal.
- `peak_to_trough_hourly_arrivals` = 9.036 (threshold 2.0): **flagged**. Ratio of busiest to quietest hour-of-day arrival rate (mean 3.11/h); the twin assumes a constant rate.

Baseline fit under normal demand (twin vs truth):

| Metric | Truth | Twin | Relative error |
|---|---|---|---|
| cycle_median_hours | 11.604 | 2.943 | -0.746 |
| cycle_p95_hours | 23.515 | 7.235 | -0.692 |
| completion_rate | 0.969 | 0.988 | 0.020 |
| sla_attainment | 0.721 | 0.987 | 0.369 |
| objective_cost_per_case | 130.440 | 118.181 | -0.094 |

| Condition | Method | Kendall τ vs truth | Objective MAPE | Choice | Truth regret | Choice feasible in truth |
|---|---|---|---|---|---|---|
| normal | capacity_aware_twin | 0.970 | 0.061 | baseline | n/a | no |
| normal | uncapacitated_sim | 0.748 | 0.092 | baseline | n/a | no |
| normal | spreadsheet | 0.748 | 0.087 | baseline | n/a | no |
| normal | truth best feasible | — | — | alt-4-3-1-ml_assisted-fifo | — | — |
| surge_25 | capacity_aware_twin | 0.788 | 0.091 | alt-3-4-1-ml_assisted-high_value_first | 0.00 | yes |
| surge_25 | uncapacitated_sim | 0.626 | 0.164 | baseline | n/a | no |
| surge_25 | spreadsheet | 0.626 | 0.157 | alt-3-4-1-ml_assisted-high_value_first | 0.00 | yes |
| surge_25 | truth best feasible | — | — | alt-3-4-1-ml_assisted-high_value_first | — | — |

Kept at authored values (not observable in history): `classify.ml_assisted`, `classify_review.manual (too few observations)`

### H2: budgeted selection (on the twin)

10 alternatives; long-run means from 60 replications; gap best to second 0.03; 2 alternative(s) within δ = 1.0; 400 macro-replications from a pool of 40.

| Budget | PCS equal (±SE) | PCS OCBA (±SE) |
|---|---|---|
| 50 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 100 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 150 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 200 | 1.000 ± 0.000 | 1.000 ± 0.000 |

### H3: robustness across bootstrap parameter worlds

12 worlds × 4 replications. Point choice `baseline`; minimax-regret choice `baseline`; point choice fragile (feasible in < 80% of worlds): no.

In the hidden truth under held-out +25% demand:

- point choice: objective 122.92, meets rule no, regret n/a
- robust choice: objective 122.92, meets rule no, regret n/a
- basis for H3: neither choice meets the decision rule in truth; compared on truth objective only


## support

### H1: hidden-truth validation

History: 960 h, 6639 arrivals (seed 500). Hidden mechanisms: Truth adds 0.15h handoff delays, 10% per-shift absenteeism and a daily peak.

Residual diagnostics on the baseline log:

- `mean_handoff_gap_hours` = 0.150 (threshold 1e-06): **flagged**. The twin assumes zero time between steps; a positive gap means unmodelled handoff delay.
- `idle_capacity_while_queued` = 0.856 (threshold 0.05): **flagged**. Share of time work waited although fewer than the nominal servers were busy (worst resource: qa_lead); suggests effective capacity below nominal.
- `peak_to_trough_hourly_arrivals` = 9.339 (threshold 2.0): **flagged**. Ratio of busiest to quietest hour-of-day arrival rate (mean 6.92/h); the twin assumes a constant rate.

Baseline fit under normal demand (twin vs truth):

| Metric | Truth | Twin | Relative error |
|---|---|---|---|
| cycle_median_hours | 10.780 | 1.947 | -0.819 |
| cycle_p95_hours | 19.984 | 5.337 | -0.733 |
| completion_rate | 0.961 | 0.994 | 0.033 |
| sla_attainment | 0.579 | 0.993 | 0.714 |
| objective_cost_per_case | 110.654 | 103.732 | -0.063 |

| Condition | Method | Kendall τ vs truth | Objective MAPE | Choice | Truth regret | Choice feasible in truth |
|---|---|---|---|---|---|---|
| normal | capacity_aware_twin | 0.727 | 0.071 | alt-4-6-3-manual-fifo | n/a | no |
| normal | uncapacitated_sim | 0.576 | 0.097 | alt-4-6-3-manual-fifo | n/a | no |
| normal | spreadsheet | 0.576 | 0.096 | alt-4-6-4-auto_classify-fifo | n/a | no |
| normal | truth best feasible | — | — | None | — | — |
| surge_25 | capacity_aware_twin | 0.576 | 0.033 | None | n/a | n/a |
| surge_25 | uncapacitated_sim | 0.788 | 0.146 | alt-4-6-3-manual-fifo | n/a | no |
| surge_25 | spreadsheet | 0.788 | 0.151 | baseline | n/a | no |
| surge_25 | truth best feasible | — | — | None | — | — |

Kept at authored values (not observable in history): `routing.auto_classify`, `misroute_fix.manual (too few observations)`

### H2: budgeted selection (on the twin)

10 alternatives; long-run means from 60 replications; gap best to second 0.02; 2 alternative(s) within δ = 1.0; 400 macro-replications from a pool of 40.

| Budget | PCS equal (±SE) | PCS OCBA (±SE) |
|---|---|---|
| 50 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 100 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 150 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 200 | 1.000 ± 0.000 | 1.000 ± 0.000 |

### H3: robustness across bootstrap parameter worlds

12 worlds × 4 replications. Point choice `alt-4-6-3-manual-fifo`; minimax-regret choice `alt-4-6-4-auto_classify-fifo`; point choice fragile (feasible in < 80% of worlds): yes.

In the hidden truth under held-out +25% demand:

- point choice: objective 86.26, meets rule no, regret n/a
- robust choice: objective 94.36, meets rule no, regret n/a
- basis for H3: neither choice meets the decision rule in truth; compared on truth objective only

## Reading these results

- The hidden truth is itself a simulator written by the same authors; agreement with it is evidence about structural robustness to the listed mechanisms only, not about real operations.
- Regret is measured against the lowest truth objective among the evaluated alternatives, not against the global optimum.
- With three packs, hypothesis outcomes are descriptive; no multiplicity-corrected significance claim is made.
