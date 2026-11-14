# Reconstruction pack for `release-8cb0f29e2297`

Generated 2026-11-14T19:57:38.631751+00:00. Hash chain verified.

| Recorded at | Valid from | Record | Kind | Edges |
|---|---|---|---|---|
| 2026-11-14T19:57:38.593192+00:00 | 2026-11-14T19:57:38.593192+00:00 | `request-6f398fae5964` | request | — |
| 2026-11-14T19:57:38.595720+00:00 | 2026-11-14T19:57:38.595720+00:00 | `proposal-5ba3c5cea022` | proposal | derived_from → `request-6f398fae5964` |
| 2026-11-14T19:57:38.598052+00:00 | 2026-11-14T19:57:38.598052+00:00 | `experiment-c14ddb3c474d` | experiment | evaluates → `proposal-5ba3c5cea022` |
| 2026-11-14T19:57:38.601300+00:00 | 2026-11-14T19:57:38.601300+00:00 | `brief-2cfe2a526865` | brief | derived_from → `experiment-c14ddb3c474d` |
| 2026-11-14T19:57:38.603320+00:00 | 2026-11-14T19:57:38.603320+00:00 | `trust_assessment-b6c587dd7f11` | trust_assessment | — |
| 2026-11-14T19:57:38.609102+00:00 | 2026-11-14T19:57:38.609102+00:00 | `change_package-3a9f1d7a694c` | change_package | derived_from → `brief-2cfe2a526865`, assessed_by → `trust_assessment-b6c587dd7f11` |
| 2026-11-14T19:57:38.617278+00:00 | 2026-11-14T19:57:38.617278+00:00 | `approval-41c960dbaab4` | approval | approves → `change_package-3a9f1d7a694c` |
| 2026-11-14T19:57:38.619801+00:00 | 2026-11-14T19:57:38.619801+00:00 | `approval-73489c2850f7` | approval | approves → `change_package-3a9f1d7a694c` |
| 2026-11-14T19:57:38.626197+00:00 | 2026-11-14T19:57:38.626197+00:00 | `release-8cb0f29e2297` | release | releases → `change_package-3a9f1d7a694c`, authorised_by → `approval-41c960dbaab4`, authorised_by → `approval-73489c2850f7` |
