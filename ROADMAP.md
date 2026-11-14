# Roadmap and open implementation points

These are known gaps, listed openly so they can be picked up later. Each item gives its
motivation, a concrete plan and acceptance criteria. Items 1 to 4 are the main remaining
credibility gaps, ordered by their value relative to effort.

---

## 1. Measured real-model evaluation (highest priority)

**Gap.** Every proposal result so far comes from compiled rules written by the same authors as
the labelled requests, so no real-model performance is claimed.

**Plan.**
1. Run `ops-twin eval-routing --provider anthropic --model claude-haiku-5-5 --max-cost-usd 0.25`.
   The model is used only as the escalation tier for requests the compiled rules skip.
2. Run the model as the sole proposer on all 36 labelled requests, reporting each split
   separately: `ops-twin eval-agent --provider anthropic ... --split heldout`.
3. Run shadow mode on the requests the compiled rules accept, and report the agreement rate.
4. Commit `results/agent/*-claude-haiku-5-5.{json,md}`. Record the requested and reported model
   IDs, tokens, latency, estimated cost (from `prices.toml`, re-verified on the run date) and the
   run date.
5. Add a README table with four rows: compiled rules only, model only, routed (compiled, then
   model) and shadow agreement. Report correct, wrong, skipped and invalid-output counts.

**Acceptance criteria.**
- Real usage is recorded, with total cost under the cap.
- Results are reported for the dev and held-out splits separately.
- Wrong answers and invalid outputs are counted, never hidden.
- Control-removal requests that became runnable remain at 0.

**Estimated cost.** About $0.01–0.02 at the recorded Claude Haiku 5.5 price. Requires
`ANTHROPIC_API_KEY` or an active `ant auth login` profile.

---

## 2. Authenticated approval identities

**Gap.** Approvals are HMAC tokens made from local secrets in `.ops-twin/keyring.json`, so
identities are illustrative.

**Plan.**
1. Replace HMAC with **asymmetric signatures (Ed25519)**. Reviewers hold private keys, and the
   repository or service holds only a public-key registry, so the verifier can't forge
   approvals.
2. Add key lifecycle: register, rotate and revoke. Revocation is a provenance-graph
   invalidation, so as-of queries show which keys were valid at approval time.
3. Optionally bind identity to an external provider (OIDC or SSO). The signed token then carries
   the subject claim, and the release checks verify issuer and audience.
4. Extend the harness evaluation with negative tests for revoked keys, keys signing outside
   their validity window, and unknown signers.

**Acceptance criteria.**
- No secret that can create approvals is stored where the release step runs.
- All existing negative tests still pass, plus the new key-lifecycle tests.

---

## 3. Connector to a real (staging) system of record

**Gap.** The system of record is a local JSON sandbox, and nothing connects to an operational
system.

**Plan.**
1. Define a `SystemOfRecord` protocol with `read`, `stage_write` and `read_back` methods.
   Writes carry idempotency keys and a precondition (an ETag or version of the quoted "before"
   state).
2. Build one adapter against a **staging** instance, for example a staffing or rostering table
   behind a REST API or a database view. It is read-only by default, and writes are enabled per
   object type.
3. Keep every current release check. Add a precondition-failure check (the remote state
   changed) and a partial-failure path that records a refusal without retrying silently.
4. Add contract tests against a recorded or fake server. A live run happens only against
   staging, never production.

**Acceptance criteria.**
- The golden jobs pass against the staging adapter.
- Each negative test leaves the remote record unchanged, confirmed by a read-back.
- Writes are idempotent under replay.

---

## 4. Validation against observed (real or public) data

**Gap.** All three packs are synthetic and hand-authored, so nothing is validated against real
operations.

**Plan.**
1. Choose a public, appropriately licensed event log with resource and timestamp information.
   Candidates are the BPI Challenge logs (for example procurement, loan applications or
   incident management). Check each licence first.
2. Write an importer from that log into a pack: steps, resources, routing and calibrated
   service times. Record which parameters were observed and which were assumed.
3. Run the trust gate on the observed log, and report its residual diagnostics as they come out.
4. Validate the baseline only: compare simulated against observed throughput and cycle-time
   distributions on a held-out time window. State clearly that a good baseline fit does not
   validate interventions.

**Acceptance criteria.**
- A licensed, versioned importer exists.
- Calibration, diagnostics and baseline-fit results are committed with the time-window split.
- Every claim is limited to baseline accuracy.

---

## Further improvements

| Area | Item |
|---|---|
| Decision science | Apply decision rules to interval bounds rather than means, and use sequential replication stopping in the main study. |
| Decision science | Re-run H2 on a harder shortlist, so that more than one alternative isn't already inside the indifference zone. |
| Engine | Add shifts and calendars, abandonment, preemption, batching, and automation error that depends on load. |
| Research | Add more hidden-truth families (for example load-dependent fallout and learning effects), and a fourth domain pack held out from development. |
| Routing | Promote compiled rules from shadow-mode agreements, via a reviewed rule diff with regression tests. |
| Governance | Expire stale change packages automatically, and add a rollback package flow (a reverse change that needs its own approvals). |
| Delivery | Coverage badge from CI (currently a static number), and a hosted results dashboard alongside the docs. |
