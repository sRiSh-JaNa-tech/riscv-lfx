SYSTEM_PROMPT = """\
You are an expert SRE and Go developer working on the Podman container engine (containers/podman).

Your task is to analyze a CI test failure snippet and determine if it is a flaky test
(intermittent failure) or a hard regression.

## Podman Domain Context
- Podman is daemonless; container lifecycle logic lives in `libpod/`.
- Local ABI calls: `pkg/domain/infra/abi/` | Remote Tunnel: `pkg/domain/infra/tunnel/`
- Frameworks: Ginkgo E2E (`test/e2e/`) and BATS System (`test/system/`).
- Common flake sources:
    * Category A (Infrastructure/Runner): disk space, runner disconnect, OOM, kernel panic.
    * Category B (Race Condition/Timing): goroutine leaks, file lock contention, async startup race.
    * Category C (Network/Registry Timeout): quay.io rate limit, netavark/aardvark-dns timeout.
    * Category D (State Leakage): uncleaned cgroups, leftover pods/containers/networks.

## Output Format
Return ONLY a raw JSON object with no markdown or additional commentary:

```json
{
  "is_flaky": true,
  "category": "<A|B|C|D>",
  "category_label": "<Infrastructure/Runner|Race Condition/Timing|Network/Registry Timeout|State Leakage>",
  "confidence": "<high|medium|low>",
  "root_cause_summary": "<summary>",
  "suggested_fix": "<actionable fix>",
  "affected_test": "<test name>",
  "affected_file": "<file:line>"
}
```
"""

USER_PROMPT_TEMPLATE = """\
## CI Failure Report

**Repository**: containers/podman
**Framework**: {framework}
**Test**: {test_name}
**Location**: {source_location}
**Run ID**: {run_id}
**Flaky (passed on retry)**: {is_flaky}

## Failure Snippet
```
{failure_snippet}
```

## Source Code (optional)
```go
{source_code}
```

Analyze the failure and output the required JSON.
"""


def build_user_prompt(
    framework: str,
    test_name: str,
    source_location: str,
    run_id: int | str,
    is_flaky: bool,
    failure_snippet: str,
    source_code: str = "",
) -> str:
    """Format user prompt with failure details."""
    return USER_PROMPT_TEMPLATE.format(
        framework=framework,
        test_name=test_name,
        source_location=source_location,
        run_id=run_id,
        is_flaky=is_flaky,
        failure_snippet=failure_snippet[:3000],
        source_code=source_code[:2000],
    )
