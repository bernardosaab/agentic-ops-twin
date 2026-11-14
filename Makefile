# Common tasks. Every target is a thin wrapper around a documented command, so nothing here is
# required: copy the command if you do not use make (for example on Windows without make).
.PHONY: help install lint format typecheck test cov check demo reproduce figures docs docs-serve api clean

PY ?= python

help:  ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install:  ## Install with all optional extras for development
	$(PY) -m pip install -e ".[dev,llm,viz,docs]"

lint:  ## Ruff lint and format check
	ruff check . && ruff format --check .

format:  ## Apply ruff formatting and safe fixes
	ruff check . --fix && ruff format .

typecheck:  ## mypy (strict on the simulation core)
	mypy src

test:  ## Run the test suite
	pytest -q

cov:  ## Tests with coverage report
	pytest -q --cov=agentic_ops_twin --cov-report=term-missing

check: lint typecheck test  ## Everything CI runs

demo:  ## Two-minute offline demo on the insurance pack
	ops-twin study --pack insurance --profile quick
	ops-twin propose --pack insurance "Automate triage under the surge scenario." --run
	ops-twin propose --pack insurance "Skip the fraud check under normal demand."
	ops-twin ledger verify

reproduce:  ## Regenerate every committed result and figure (~10 min on 6 cores)
	ops-twin study --pack all --profile full
	ops-twin research --pack all
	ops-twin eval-agent --provider fake
	ops-twin brief --pack insurance && ops-twin brief --pack procurement && ops-twin brief --pack support
	ops-twin ledger verify
	ops-twin figures

figures:  ## Re-render README/docs figures from results/
	ops-twin figures

docs:  ## Build the documentation site into site/
	mkdocs build --strict

docs-serve:  ## Serve the documentation locally
	mkdocs serve

api:  ## Local API on http://127.0.0.1:8000/docs
	uvicorn agentic_ops_twin.api:app --host 127.0.0.1 --port 8000

clean:  ## Remove caches and build output
	rm -rf .pytest_cache .mypy_cache .ruff_cache site dist build .coverage
