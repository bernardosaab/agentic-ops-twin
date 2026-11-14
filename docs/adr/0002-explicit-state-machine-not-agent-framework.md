# ADR 0002: Explicit proposal state machine instead of an agent framework

**Status:** accepted

**Context.** The blueprint suggests LangGraph for scenario proposal and review. The required
flow is small: propose, critique, at most one repair, then stop. It also has to behave the same
for a scripted fake and for a real model.

**Decision.** Implement the flow as a plain four-state loop in `agent/loop.py`, with typed
attempts and outcomes. Do not add LangGraph.

**Consequences.**
- There is no extra dependency, and every transition can be tested directly.
- If multi-agent review, persistence of graph state, or human-in-the-loop interrupts become
  necessary, revisit this choice.
