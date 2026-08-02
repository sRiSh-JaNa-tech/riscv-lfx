# Podman Flaky Test Analyzer — Sample Code

This directory contains **sample/prototype code** for the *Automated Flaky Test
Analysis & Reporting Toolchain* proposed in [LFX_PROPOSAL.md](../LFX_PROPOSAL.md)
and [architecture-plan-proposal.md](../architecture-plan-proposal.md).

> **Note**: This is illustrative code for the LFX proposal — not yet integrated
> into the main Podman build system. The final implementation will live under
> `hack/ci/flaky-analyzer/` in the repository root.

---

## Directory Layout

```
sample-code/
├── ingestion/
│   ├── __init__.py
│   ├── github_client.py      # GitHub REST API wrapper (runs, jobs, logs, issues)
│   └── retry_detector.py     # Flake vs. hard-failure classifier via retry analysis
├── parsers/
│   ├── __init__.py
│   ├── ginkgo_parser.py      # Ginkgo E2E log parser  (test/e2e/)
│   └── bats_parser.py        # BATS system test parser (test/system/)
├── agent/
│   ├── __init__.py
│   ├── prompts.py            # System & user prompt templates with Podman context
│   └── llm_client.py         # LiteLLM wrapper + FlakeAnalysisResult dataclass
├── reporter/
│   ├── __init__.py
│   ├── deduplicator.py       # SHA-256 fingerprint + GitHub Issue search
│   └── github_reporter.py    # Issue creator / updater + PR commenter
├── tests/
│   ├── test_ginkgo_parser.py
│   ├── test_bats_parser.py
│   └── test_deduplicator.py
├── main.py                   # CLI entry point (--run-id, --log-file, --pr, --dry-run)
├── flaky-test-analyzer.yml   # GitHub Actions workflow (drop into .github/workflows/)
└── pyproject.toml            # Python project metadata & dependencies
```

---

## Pipeline Overview

```
CI Failure
    │
    ▼
ingestion/github_client.py   ← GitHub REST API: runs, jobs, logs
    │
    ▼
ingestion/retry_detector.py  ← Did attempt 1 fail and attempt 2 pass? → is_flaky
    │
    ▼
parsers/ginkgo_parser.py     ← Extract spec name, go:line, assertion
parsers/bats_parser.py       ← Extract test name, bats:line, command, $output
    │
    ▼
agent/llm_client.py          ← LiteLLM → FlakeAnalysisResult (JSON)
    │  (uses agent/prompts.py with Podman domain context)
    ▼
reporter/deduplicator.py     ← SHA-256(suite|test|normalized_error) → search Issues
reporter/github_reporter.py  ← Create / update Issue  +  PR comment
```

---

## Quick Start

### Configuration & API Keys
Copy `.env.sample` to `.env` and fill in your API keys:
```bash
cp .env.sample .env
```
Or export variables in your terminal:
```bash
export GITHUB_TOKEN="ghp_..."
export OPENAI_API_KEY="sk-..."
```

### Analyse a GitHub Actions run
```bash
python main.py --run-id 12345678
```

### Analyse a local log file
```bash
python main.py --log-file /tmp/ginkgo.log --framework ginkgo
```

### Dry-run (no GitHub API writes)
```bash
python main.py --run-id 12345678 --dry-run
```

### Annotate a PR
```bash
python main.py --run-id 12345678 --pr 9001
```

### Run the unit tests
```bash
python -m pytest tests/ -v
```

---

## Flake Taxonomy (Category Key)

| Code | Label | Example |
|:----:|:------|:--------|
| **A** | Infrastructure / Runner | Disk exhaustion, OOM kill, runner disconnect |
| **B** | Race Condition / Timing | Goroutine leak, async startup race, file-lock |
| **C** | Network / Registry Timeout | `quay.io` rate limit, `netavark`/`aardvark-dns` timeout |
| **D** | State Leakage | Uncleaned cgroups, leftover pods/networks from prior tests |

---

## Environment Variables

| Variable | Required | Description |
|:---------|:--------:|:------------|
| `GITHUB_TOKEN` | ✅ | Personal Access Token with `issues:write`, `pull-requests:write` |
| `OPENAI_API_KEY` | ✅ | API key for the LLM provider |
| `LITELLM_MODEL` | ❌ | Model string (default: `gpt-4o`). Any LiteLLM provider works. |
