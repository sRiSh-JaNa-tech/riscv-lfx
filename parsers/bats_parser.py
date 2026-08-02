from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_NOT_OK = re.compile(
    r"^not ok\s+(?P<index>\d+)\s+(?P<test_name>.+)$",
    re.MULTILINE,
)

_RE_BATS_LOCATION = re.compile(
    r"in test file\s+(?P<path>[^\s,]+),\s+line\s+(?P<line>\d+)",
)

_RE_FAILED_CMD = re.compile(
    r"`(?P<command>[^']+)'\s+failed\s+with\s+status\s+(?P<status>\d+)",
)

_RE_DIAG = re.compile(r"^#\s*(?P<text>.*)$", re.MULTILINE)


@dataclass
class BATSFailure:
    test_index: int
    test_name: str
    bats_file: str
    bats_line: int
    failed_command: str
    exit_status: int
    diagnostic_output: str
    raw_block: str
    framework: str = "bats"
    context_lines: list[str] = field(default_factory=list)


def parse_bats_log(raw_log: str) -> list[BATSFailure]:
    """Parse BATS system test logs and return structured failure details."""
    failures: list[BATSFailure] = []
    blocks = _split_bats_blocks(raw_log)
    for block in blocks:
        f = _parse_bats_block(block)
        if f is not None:
            failures.append(f)
    return failures


def _split_bats_blocks(log: str) -> list[str]:
    positions = [m.start() for m in _RE_NOT_OK.finditer(log)]
    if not positions:
        return []

    blocks: list[str] = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(log)
        blocks.append(log[start:end])
    return blocks


def _parse_bats_block(block: str) -> BATSFailure | None:
    header = _RE_NOT_OK.search(block)
    if not header:
        return None
    test_index = int(header.group("index"))
    test_name = header.group("test_name").strip()

    loc = _RE_BATS_LOCATION.search(block)
    bats_file = loc.group("path") if loc else ""
    bats_line = int(loc.group("line")) if loc else 0

    cmd_match = _RE_FAILED_CMD.search(block)
    failed_command = cmd_match.group("command").strip() if cmd_match else ""
    exit_status = int(cmd_match.group("status")) if cmd_match else -1

    diag_lines = [m.group("text") for m in _RE_DIAG.finditer(block)]
    diagnostic_output = "\n".join(diag_lines[:40])

    return BATSFailure(
        test_index=test_index,
        test_name=test_name,
        bats_file=bats_file,
        bats_line=bats_line,
        failed_command=failed_command,
        exit_status=exit_status,
        diagnostic_output=diagnostic_output,
        raw_block=block[:4000],
        context_lines=diag_lines[40:80],
    )
