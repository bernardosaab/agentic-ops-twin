# Assumptions, metric definitions and limitations

## Metric definitions

- **Cohort.** Cases arriving in `[warm-up, horizon)`. Warm-up arrivals load the system but
  are not counted.
- **Conservation.** `arrivals = completed + open`. It is asserted in every run, and open cases
  are split into queued, in service and in handoff.
- **Cycle times.** Median and p95 are computed on completed cohort cases only. They are always
  shown next to completion rate and open cases, so unfinished work cannot make a policy look
  fast.
- **SLA attainment.** Completed within the SLA, divided by all cohort arrivals. Open cases count
  as misses.
- **Cost.**
  - Staffed cost is capacity × hourly rate × window. It covers only resources that an active
    step uses, so an automation that is switched off costs nothing.
  - Variable cost is the per-case cost of services that start inside the window.
  - Cost per completion is window cost divided by all completions in the window.
- **Objective.** `(window cost + SLA penalty × cohort misses) / cohort arrivals`. Because
  staffed cost is spread across arrivals, higher demand can *lower* this number while service
  degrades. That is why the decision rule also constrains completion rate and SLA attainment.
- **Utilisation.** Busy server-hours divided by staffed server-hours in the window. It is
  undefined for zero or inactive capacity.
- **Uncertainty.** 95% Student-t intervals across independent replications. Paired differences
  are used only when every replication pair has an identical arrival-stream digest; otherwise
  the Welch interval is used and labelled as such.

## Modelling assumptions

- Arrivals are Poisson and stationary within a condition. The daily profile exists only in the
  hidden truth.
- Service is non-preemptive with FIFO or a two-class value priority. There is no abandonment,
  batching, shifts or calendars.
- Routing is first-match on the case value, then a probabilistic branch. Rework is bounded by
  per-edge traversal limits with an explicit fallback.
- Automation variants have fixed fallout probabilities, independent of load.
- Costs are linear.

## Scientific limitations

- Simulated counterfactuals are conditional on the model. They are not causal estimates or
  forecasts.
- A good baseline fit does not establish accuracy under intervention. The hidden-truth study
  shows this directly.
- Sensitivity varies existing parameters within stated ranges. It cannot reveal omitted
  mechanisms; the residual diagnostics address a few named ones.
- Search enumerates a small grid (at most 200 combinations). It is not a general optimiser,
  and the decision rule is applied to replication means, not to interval bounds.
- The hidden truth is written by the same authors. Agreement with it says nothing about real
  operations.
- With three packs, hypothesis outcomes are descriptive.

## Operational limitations

- This is an offline simulation prototype, not a live twin. It has no data ingestion,
  freshness checks or synchronisation.
- It never changes live systems. "Approve" records a decision for discussion only.
- The API is unauthenticated and meant for local use. Reviewer identity is self-asserted. The
  ledger is tamper-evident, not secure.
