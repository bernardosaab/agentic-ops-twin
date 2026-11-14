# Contributing

Thanks for your interest. This is a research prototype, so correctness and honest evidence
matter more than feature count.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,llm,viz,docs]"
make check   # ruff, mypy and pytest (without make, see the Makefile for the plain commands)
```

## Ground rules

- **Never weaken a control path.** Changes to `simulation/validate.py`,
  `decision/scenarios.py` or `agent/critic.py` need a test showing that controls still cannot
  be removed, bypassed or automated.
- **Reject inputs instead of guessing them.** New model fields must be required. The only
  exception is a default that doesn't change behaviour, and it must be documented.
- **Results come from runs.** Any change that can alter numbers requires `make reproduce`.
  Commit the regenerated `results/` and figures in the same pull request, and never hand-edit
  results.
- **Keep the research honest.** Don't change mechanisms, alternative sets or decision rules
  after seeing results. Instead, bump the version of `docs/preregistration.md` and re-run.
- **Use synthetic data only.**
  - No real organisational data, credentials or personal information in the repository.
  - Never send any of these to a model provider.
- **Style.** Use ruff formatting and type hints everywhere. mypy runs in strict mode on
  `simulation/`.

## Pull requests

Each pull request should cover:

- what changed;
- how you verified it;
- any effect on the committed results.

Keep pull requests focused, and add an entry to `CHANGELOG.md` under "Unreleased".
