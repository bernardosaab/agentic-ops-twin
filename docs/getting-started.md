# Getting started

## Requirements

- Python 3.11, 3.12 or 3.13, on Windows, macOS or Linux.
- CPU only. No GPU, model download or provider account is needed for the offline path.

## Install

```bash
git clone https://github.com/bernardosaab/agentic-ops-twin.git
cd agentic-ops-twin
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,viz]"        # add ,llm for the opt-in Claude adapter, ,docs for this site
```

## Two-minute tour

```bash
ops-twin packs                                   # list the three domain packs
ops-twin validate --pack insurance               # structural and control-path checks
ops-twin study --pack insurance --profile quick  # baseline ladder, search, held-out, sensitivity
ops-twin propose --pack insurance "Automate triage under the surge scenario." --run
ops-twin propose --pack insurance "Skip the fraud check under normal demand."   # rejected
ops-twin brief --pack insurance                  # grounded draft from the stored study
ops-twin review --brief <brief-record-id> --reviewer "<name>" --decision approve
ops-twin ledger verify
```

The two `propose` calls behave differently:

- The first is validated, simulated against the baseline on the held-out seeds, and summarised
  in a grounded brief.
- The second is rejected with `control_locked`, so nothing runs.

## Reproduce every published result

```bash
make reproduce     # or run the commands listed under `reproduce` in the Makefile
```

On an 8-core laptop CPU with 6 worker processes, this takes about 10 minutes. Results are
deterministic for a given seed and don't depend on the worker count (this is tested). To change
the number of workers, use `--workers N` or set `OPS_TWIN_WORKERS`.

## Quality checks

```bash
make check         # ruff lint and format, mypy (strict on the simulation core), pytest
make cov           # tests with a coverage report
```

## Local API

```bash
make api           # http://127.0.0.1:8000/docs
```

The API is unauthenticated and meant for local use only. It never calls a model provider.

## Opt-in real model

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=...
ops-twin propose --pack support "Automate routing under normal demand." \
    --provider anthropic --model claude-haiku-5-5 --max-cost-usd 0.05
ops-twin eval-agent --provider anthropic --model claude-haiku-5-5 --max-cost-usd 0.25
```

See [Agent and governance](agent-and-governance.md) for what is sent to the provider, how
spending is capped, and how usage is recorded.
