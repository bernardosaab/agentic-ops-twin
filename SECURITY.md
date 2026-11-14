# Security policy

Agentic Ops Twin is an offline research prototype, and some of its security limits are
deliberate:

- The local API is **unauthenticated**. Bind it only to `127.0.0.1`.
- Reviewer identities in the ledger are **self-asserted**.
- The hash-chained ledger is **tamper-evident**, not tamper-proof.
- The project never connects to or changes live business systems.

The opt-in model adapter reads `ANTHROPIC_API_KEY` from the environment. It never logs the key
or includes it in prompts, and `tests/test_anthropic_adapter.py` checks this.

Don't commit keys or real organisational data.

## Reporting a vulnerability

To report a vulnerability, open a GitHub security advisory: use "Report a vulnerability" on the
repository's Security tab. Please don't open a public issue. Examples of vulnerabilities:

- a way to make a control-removal proposal runnable;
- a way for secrets to reach a prompt or a log.
