# ADR 0003: Bounded enumeration instead of OR-Tools

**Status:** accepted

**Context.** The decision spaces are small discrete grids, between 72 and 108 combinations
before budget filtering. The objective is a stochastic simulation output.

**Decision.**
- Enumerate every permitted combination up to a hard cap. Exceeding the cap is an error, not a
  silent sample.
- Collapse behaviourally equivalent configurations.
- Score each one by replications.
- Select with a pre-declared rule.
- Evaluate OCBA-style replication allocation separately (research H2).

**Consequences.**
- Nothing is presented as solved by an integer solver.
- OR-Tools would become worthwhile for an explicitly formulated sub-problem, such as staffing
  to an offered-load constraint. The configurations it proposes would then be simulated.
