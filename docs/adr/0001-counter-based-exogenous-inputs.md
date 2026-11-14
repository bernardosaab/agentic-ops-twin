# ADR 0001: Counter-based exogenous inputs with verified pairing

**Status:** accepted

**Context.** Comparing policies with common random numbers lowers the variance of each
difference. But a shared seed on a sequential RNG stops lining up once two policies consume
draws in a different order or number, for example when one sends a case through an extra step.

**Decision.** Every draw is a function of
`BLAKE2b(scheme, seed, stream, case_id, step_id, visit)`. Service times use the inverse CDF, so
a uniform carries across changed distributions. Each replication records a digest of its
realised arrival stream. Comparisons pair replications only when the digests match, and
otherwise fall back to Welch intervals with a note.

**Consequences.**
- Pairing holds for capacity, variant and priority changes.
- Demand changes are correctly treated as unpaired.
- Hashing costs a few microseconds per draw.
- `tests/test_engine_invariants.py` demonstrates the sequential-RNG failure.
