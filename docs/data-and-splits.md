# Data, generation, seeds and splits

All data is synthetic. Nothing is derived from real organisations.

## Domain packs (`src/throughline/packs/*.py`, generator `packs-v1`)

Parameters are hand-authored in Python modules. These are the source of truth, and
`throughline dataset --pack <id>` exports a pack as JSON. Each pack declares:
- an operating model (version `1.0.0`);
- a bounded decision space and a staffed-cost budget;
- a pre-declared decision rule;
- demand conditions;
- seed splits;
- sensitivity ranges;
- hidden-truth mechanisms, used for validation only.

| Pack | Case types (rate/h) | Mandatory controls | Automation option |
|---|---|---|---|
| insurance | standard 3.0, complex 0.6 | fraud check and senior approval for value ≥ 10,000 | automated triage with 22% fallout to adjuster review |
| procurement | price mismatch 2.0, missing receipt 1.0 | three-way match (all); segregation-of-duties approval ≥ 10,000 | ML-assisted classification with 25% fallout to clerk review |
| support | billing 4.0, technical 3.0 | QA review for refunds ≥ 500 | automated routing with 25% misroutes fixed by tier 1 |

The horizon is 320 operating hours with a 40-hour warm-up. Time is continuous operating time,
with no calendar.

## Case streams

Arrivals, case values, service-time uniforms and routing uniforms are pure functions of
`(seed, stream, keys)` under scheme `blake2b-counter-v1`. To export one seed's arrivals and
event log as CSV:

```bash
throughline dataset --pack insurance --seed 1000 --condition normal
```

## Seeds and splits

| Use | Seeds | Conditions |
|---|---|---|
| Search (selection) | 1000–1009 (quick profile: 1000–1003) | normal |
| Held-out evaluation | 9000–9019 (quick: 9000–9005) | normal, surge_25 (+25%), and one pack-specific shifted mix |
| Hidden-truth history (calibration) | 500 (one 960-hour run) | normal with daily profile |
| Hidden-truth validation | 7000–7007 | normal, surge_25 |
| Robustness worlds | 8000–8003 per world; bootstrap seeds 10000+w | normal |
| Selection pool / long-run reference | 30000–30039 / 20000–20059 | normal |

Disjointness of the search and held-out splits is enforced by `Splits` and tested.

## Labelled requests (`packs/data/requests.json`, `requests-v1`)

There are 36 hand-written requests, 12 per pack. They are split into 18 dev and 18 held-out.
The categories are:
- normal;
- missing values;
- contradictory;
- control removal;
- out of scope;
- out of bounds;
- over budget.

The same authors wrote both the requests and the scripted fake. The dev requests were visible
while the fake's rules were written, so its score is not an AI measurement.

## Assumptions shared by generator and implementation

- The hidden truth reuses the pack's routing structure, steps and authored automation-variant
  parameters. It adds only handoff delay, absenteeism and a daily arrival profile.
  Mechanisms outside these three are not tested.
- The labelled requests use vocabulary that the scripted fake's synonym table also contains.
