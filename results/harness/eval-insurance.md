# Harness evaluation: governed write path (insurance)

**14/14 cases passed.** A refusal passes only if the sandboxed system of record is unchanged. This evaluates the harness, not a model: the proposer is the compiled rule path.

The reconstruction pack for the golden release links 9 records, and its hash chain is verified.

| Case | Type | Scenario | Expected | Actual | System of record unchanged | Pass |
|---|---|---|---|---|---|---|
| G1 | golden | High-risk change (automation, unvalidated twin), two acknowledging approvers: written and read back | release | release | — | ✅ |
| G2 | golden | Same change with a validated twin: still high-risk (automation switch); two approvers release it | release | release | — | ✅ |
| N1 | negative | No approval at all | refusal | refusal | yes | ✅ |
| N2 | negative | High-risk package with a single approval | refusal | refusal | yes | ✅ |
| N3 | negative | Maker approves their own package (maker-checker) | refusal | refusal | yes | ✅ |
| N4 | negative | Approvals with forged tokens | refusal | refusal | yes | ✅ |
| N5 | negative | Approval tokens expired | refusal | refusal | yes | ✅ |
| N6 | negative | Unvalidated twin, approvers did not acknowledge it | refusal | refusal | yes | ✅ |
| N7 | negative | Trust gate: history shows mechanisms the twin omits | refusal | refusal | yes | ✅ |
| N8 | negative | Source brief invalidated after approval | refusal | refusal | yes | ✅ |
| N9 | negative | System of record changed after the quote (stale before-state) | refusal | refusal | yes | ✅ |
| N10 | negative | One approver rejects | refusal | refusal | yes | ✅ |
| N11 | negative | Replaying an already-released package | refusal | refusal | yes | ✅ |
| N12 | negative | Request to remove a mandatory control never becomes a change set | refusal | refusal | yes | ✅ |

## Refusal reasons recorded

- **N1**: 0 valid distinct approval(s); 2 required for a high-risk package
- **N2**: 1 valid distinct approval(s); 2 required for a high-risk package
- **N3**: approval by ops-analyst: maker/requester cannot approve; 1 valid distinct approval(s); 2 required for a high-risk package
- **N4**: approval by approver-a: token does not verify; approval by approver-b: token does not verify; 0 valid distinct approval(s); 2 required for a high-risk package
- **N5**: approval by approver-a: token expired; approval by approver-b: token expired; 0 valid distinct approval(s); 2 required for a high-risk package
- **N6**: approval by approver-a: did not acknowledge unvalidated twin; approval by approver-b: did not acknowledge unvalidated twin; 0 valid distinct approval(s); 2 required for a high-risk package
- **N7**: trust gate: twin is inadequate (release blocked: history shows mechanisms the twin omits (mean_handoff_gap_hours, idle_capacity_while_queued, peak_to_trough_hourly_arrivals))
- **N8**: source brief has been invalidated
- **N9**: system of record changed since the quote (stale before-state)
- **N10**: rejected by approver-b; 1 valid distinct approval(s); 2 required for a high-risk package
- **N11**: package was already released; system of record changed since the quote (stale before-state)
- **N12**: control_locked
