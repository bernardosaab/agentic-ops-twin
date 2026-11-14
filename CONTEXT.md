# Domain language

- **Operating model:** a versioned, digest-bound description of case types, resources, steps,
  routing, costs, controls and assumptions.
- **Step variant:** one way of performing a step, such as manual or automated. Only the active
  variant runs.
- **Mandatory control:** a step that every applicable case must pass. It is trusted input and
  cannot be changed by any lever.
- **Lever / decision space:** the only permitted changes: capacity, variant and queue policy.
  Each has bounds, and the space has a staffed-cost budget.
- **Alternative:** one combination of lever values. **Baseline** is the current configuration.
- **Cohort:** cases arriving after warm-up. **Open:** cohort cases unfinished at the horizon.
- **Exogenous inputs:** arrivals, case values, service-time uniforms and routing uniforms. They
  are counter-based and digest-verified for pairing.
- **Search split / held-out split:** disjoint seeds and conditions used for selection and for
  evaluation respectively.
- **Hidden truth:** a richer simulator used only to test whether the twin's advice survives
  mechanisms the twin omits.
- **Proposal / critique:** the untrusted structured output of a proposer, and the trusted
  deterministic verdict on it.
- **Brief / review:** an evidence-linked draft and a named decision recorded in the ledger.
  Neither deploys anything.
