from __future__ import annotations

import hashlib
import logging
import re

from ingestion.github_client import GitHubClient

logger = logging.getLogger(__name__)

FLAKE_LABEL = "ci/flaky"
REPO = "containers/podman"

# Patterns to strip from error strings before hashing (hex addresses, timestamps, pids, etc.)
_VOLATILE_PATTERNS: list[re.Pattern] = [
    re.compile(r"0x[0-9a-fA-F]{4,}"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b", re.IGNORECASE),
    re.compile(r"\bpid\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bport\s+\d{4,5}\b", re.IGNORECASE),
    re.compile(r"/tmp/[^\s]+"),
    re.compile(r"\brun-\w+\b"),
]


def _normalize_error(raw_error: str) -> str:
    """Clean error string by removing volatile numbers and timestamps."""
    result = raw_error.lower().strip()
    for pattern in _VOLATILE_PATTERNS:
        result = pattern.sub("", result)
    result = re.sub(r"\s+", " ", result)
    return result


def compute_signature(
    test_suite: str,
    test_name: str,
    error_string: str,
) -> str:
    """Compute SHA-256 fingerprint for a test failure."""
    normalized = _normalize_error(error_string)
    payload = f"{test_suite}|{test_name}|{normalized}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    logger.debug("Signature for %s / %s: %s", test_suite, test_name, digest[:16])
    return digest


def find_existing_issue(
    client: GitHubClient,
    signature: str,
) -> dict | None:
    """Search GitHub for open issues containing the signature tag."""
    short_sig = signature[:12]
    query = (
        f"repo:{REPO} is:issue is:open label:{FLAKE_LABEL} "
        f"\"flake-sig:{short_sig}\" in:body"
    )
    results = client.search_issues(query)
    if results:
        logger.info("Found existing flake issue #%s for sig=%s", results[0]["number"], short_sig)
        return results[0]
    logger.info("No existing issue found for sig=%s", short_sig)
    return None
