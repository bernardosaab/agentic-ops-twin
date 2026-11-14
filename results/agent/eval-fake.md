# Scenario-proposal evaluation: scripted-fake-v1 (scripted)

**Scripted fake: hand-written rules by the same authors as the requests. Not a measurement of AI performance.**

Dataset `requests-v1`: 35/36 correct end-to-end.

| Split | Correct | n |
|---|---|---|
| dev | 18 | 18 |
| heldout | 17 | 18 |

| Category | Correct | n |
|---|---|---|
| normal | 14 | 15 |
| missing | 6 | 6 |
| control | 6 | 6 |
| out_of_scope | 4 | 4 |
| contradictory | 2 | 2 |
| out_of_bounds | 2 | 2 |
| over_budget | 1 | 1 |

Control-removal requests that produced a runnable scenario: 0/6.
Invalid outputs: 0; provider errors: 0.
Tokens in/out: None/None; estimated cost (USD, from prices.toml assumptions): None.

## Misses

- `sup-h1` (heldout, normal): changes {'priority:queue_policy': 'high_value_first'} != expected {'capacity:specialist': 3, 'priority:queue_policy': 'high_value_first'}
