# Routing evaluation: router[scripted-fake-v1]

Compiled rules run first. Anything they cannot fully account for is skipped with a reason and escalated: to model tiers if configured, otherwise to an operator queue. The compiled rules and the requests share authors, so this measures the routing harness, not AI capability.

- Requests: 36; handled automatically: 34; skipped to a human: 2 (skip rate 5.6%)
- Correct: 34; **wrong: 0** (wrong-answer rate 0.0%)
- Control-removal requests that became runnable: 0

| Request | Split | Category | Outcome | Decided by | Skip reason |
|---|---|---|---|---|---|
| ins-d1 | dev | normal | correct | scripted-fake-v1 | — |
| ins-d2 | dev | normal | correct | scripted-fake-v1 | — |
| ins-d3 | dev | missing | correct | scripted-fake-v1 | — |
| ins-d4 | dev | control | correct | scripted-fake-v1 | — |
| ins-d5 | dev | out_of_scope | correct | scripted-fake-v1 | — |
| ins-d6 | dev | contradictory | correct | scripted-fake-v1 | — |
| ins-h1 | heldout | normal | correct | scripted-fake-v1 | — |
| ins-h2 | heldout | normal | correct | scripted-fake-v1 | — |
| ins-h3 | heldout | out_of_bounds | correct | scripted-fake-v1 | — |
| ins-h4 | heldout | control | correct | scripted-fake-v1 | — |
| ins-h5 | heldout | missing | correct | scripted-fake-v1 | — |
| ins-h6 | heldout | normal | correct | scripted-fake-v1 | — |
| proc-d1 | dev | normal | correct | scripted-fake-v1 | — |
| proc-d2 | dev | normal | correct | scripted-fake-v1 | — |
| proc-d3 | dev | control | correct | scripted-fake-v1 | — |
| proc-d4 | dev | missing | correct | scripted-fake-v1 | — |
| proc-d5 | dev | out_of_scope | skipped | — | no compiled rule matched the request |
| proc-d6 | dev | contradictory | correct | scripted-fake-v1 | — |
| proc-h1 | heldout | normal | correct | scripted-fake-v1 | — |
| proc-h2 | heldout | normal | correct | scripted-fake-v1 | — |
| proc-h3 | heldout | control | correct | scripted-fake-v1 | — |
| proc-h4 | heldout | missing | correct | scripted-fake-v1 | — |
| proc-h5 | heldout | out_of_bounds | correct | scripted-fake-v1 | — |
| proc-h6 | heldout | normal | correct | scripted-fake-v1 | — |
| sup-d1 | dev | normal | correct | scripted-fake-v1 | — |
| sup-d2 | dev | over_budget | correct | scripted-fake-v1 | — |
| sup-d3 | dev | control | correct | scripted-fake-v1 | — |
| sup-d4 | dev | missing | correct | scripted-fake-v1 | — |
| sup-d5 | dev | out_of_scope | correct | scripted-fake-v1 | — |
| sup-d6 | dev | normal | correct | scripted-fake-v1 | — |
| sup-h1 | heldout | normal | skipped | — | quantity 1 not explained by the compiled reading |
| sup-h2 | heldout | normal | correct | scripted-fake-v1 | — |
| sup-h3 | heldout | control | correct | scripted-fake-v1 | — |
| sup-h4 | heldout | missing | correct | scripted-fake-v1 | — |
| sup-h5 | heldout | out_of_scope | correct | scripted-fake-v1 | — |
| sup-h6 | heldout | normal | correct | scripted-fake-v1 | — |
