from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_FAILED_SPEC = re.compile(
    r"^\[FAILED\]\s+(?P<spec>.+)$",
    re.MULTILINE,
)

_RE_IT_SPEC = re.compile(
    r"^\s+\[It\]\s+(?P<spec>.+)$",
    re.MULTILINE,
)

_RE_SOURCE_LOCATION = re.compile(
    r"(?P<path>[/\w.\-]+\.go):(?P<line>\d+)",
)

_RE_ASSERTION = re.compile(
    r"(?:Expected|Error|panic).*",
    re.DOTALL | re.MULTILINE,
)

_RE_SUMMARY = re.compile(
    r"Ran\s+\d+\s+of\s+\d+\s+Specs.*?(?:FAILED|passed)",
    re.IGNORECASE,
)


@dataclass
class GinkgoFailure:
    spec_name: str
    source_file: str
    source_line: int
    assertion_snippet: str
    raw_block: str
    framework: str = "ginkgo"
    context_lines: list[str] = field(default_factory=list)


def parse_ginkgo_log(raw_log: str) -> list[GinkgoFailure]:
    """Parse raw Ginkgo log text and extract structured spec failure details."""
    failures: list[GinkgoFailure] = []
    blocks = _split_into_failure_blocks(raw_log)

    for block in blocks:
        failure = _parse_single_block(block)
        if failure is not None:
            failures.append(failure)

    return failures


def _split_into_failure_blocks(log: str) -> list[str]:
    separator = re.compile(
        r"(?=^-{5,}$|^={5,}$|^\[FAILED\])",
        re.MULTILINE,
    )
    parts = separator.split(log)
    return [p.strip() for p in parts if len(p.strip()) > 30]


def _parse_single_block(block: str) -> GinkgoFailure | None:
    spec_name = ""
    m = _RE_FAILED_SPEC.search(block)
    if m:
        spec_name = m.group("spec").strip()
    else:
        m = _RE_IT_SPEC.search(block)
        if m:
            spec_name = m.group("spec").strip()

    if not spec_name:
        return None

    source_file = ""
    source_line = 0
    for loc_match in _RE_SOURCE_LOCATION.finditer(block):
        path = loc_match.group("path")
        if "_test.go" in path or "e2e" in path:
            source_file = path
            source_line = int(loc_match.group("line"))
            break
    if not source_file:
        loc_match = _RE_SOURCE_LOCATION.search(block)
        if loc_match:
            source_file = loc_match.group("path")
            source_line = int(loc_match.group("line"))

    first_lines = block.splitlines()[:20]
    assertion_snippet = "\n".join(first_lines)
    context_lines = block.splitlines()[20:80]

    return GinkgoFailure(
        spec_name=spec_name,
        source_file=source_file,
        source_line=source_line,
        assertion_snippet=assertion_snippet,
        raw_block=block[:4000],
        context_lines=context_lines,
    )
