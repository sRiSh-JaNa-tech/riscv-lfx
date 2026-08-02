#!/usr/bin/env python3
"""
CLI entry point for analyzing Podman CI test failures.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from ingestion import GitHubClient, detect_flake
from parsers import parse_ginkgo_log, parse_bats_log
from agent import FlakeAnalysisAgent
from reporter import report_failure

def _load_env_file() -> None:
    """Load key-value pairs from .env into os.environ if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

_load_env_file()



def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analyze-ci-flake",
        description="Podman Flaky Test Analyzer - parses CI logs and reports flaky tests.",
    )
    p.add_argument("--run-id", type=int, help="GitHub Actions run ID to analyze.")
    p.add_argument("--log-file", help="Path to a local log file.")
    p.add_argument(
        "--framework",
        choices=["ginkgo", "bats", "auto"],
        default="auto",
        help="Test framework to use for parsing (default: auto)",
    )
    p.add_argument("--pr", type=int, default=None, help="PR number to comment on.")
    p.add_argument("--repo", default="containers/podman", help="Target GitHub repository.")
    p.add_argument("--dry-run", action="store_true", help="Print report without writing to GitHub.")
    p.add_argument("--output-json", help="Path to save JSON output.")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging.")
    return p


def run(args: argparse.Namespace) -> int:
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token and not args.log_file:
        logger.error("GITHUB_TOKEN environment variable is required when using --run-id.")
        return 1

    client = GitHubClient(token=token, repo=args.repo)
    agent = FlakeAnalysisAgent()
    results: list[dict] = []

    # Get log content
    if args.log_file:
        logger.info("Reading log from local file: %s", args.log_file)
        with open(args.log_file, encoding="utf-8", errors="replace") as fh:
            raw_log = fh.read()
        is_flaky = False
        run_id = "local"
        framework_hint = args.framework
    else:
        if not args.run_id:
            logger.error("Provide either --run-id or --log-file.")
            return 1

        logger.info("Checking retry status for run_id=%s", args.run_id)
        retry = detect_flake(client, args.run_id)
        is_flaky = retry.is_flaky
        run_id = args.run_id

        if not retry.failed_job_ids:
            logger.warning("No failed jobs found for run_id=%s.", run_id)
            return 0

        job_id = retry.failed_job_ids[0]
        logger.info("Downloading log for job_id=%s", job_id)
        raw_log = client.get_job_log(job_id)
        framework_hint = "auto"

    # Parse logs
    ginkgo_failures = []
    bats_failures = []

    if framework_hint in ("ginkgo", "auto"):
        ginkgo_failures = parse_ginkgo_log(raw_log)
        logger.info("Parsed %d Ginkgo failure(s).", len(ginkgo_failures))

    if framework_hint in ("bats", "auto"):
        bats_failures = parse_bats_log(raw_log)
        logger.info("Parsed %d BATS failure(s).", len(bats_failures))

    if not ginkgo_failures and not bats_failures:
        logger.warning("No test failures found in log.")
        return 0

    # Run AI analysis and reporting
    for failure in ginkgo_failures:
        analysis = agent.analyse(
            framework="ginkgo",
            test_name=failure.spec_name,
            source_location=f"{failure.source_file}:{failure.source_line}",
            run_id=run_id,
            is_flaky=is_flaky,
            failure_snippet=failure.assertion_snippet,
        )
        _handle_result(client, analysis, run_id, "ginkgo", args)
        results.append(_result_to_dict(analysis, run_id))

    for failure in bats_failures:
        analysis = agent.analyse(
            framework="bats",
            test_name=failure.test_name,
            source_location=f"{failure.bats_file}:{failure.bats_line}",
            run_id=run_id,
            is_flaky=is_flaky,
            failure_snippet=failure.diagnostic_output,
        )
        _handle_result(client, analysis, run_id, "bats", args)
        results.append(_result_to_dict(analysis, run_id))

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        logger.info("Results saved to %s", args.output_json)

    return 0


def _handle_result(
    client: GitHubClient,
    analysis,
    run_id,
    test_suite: str,
    args: argparse.Namespace,
) -> None:
    print(
        f"\n{'='*60}\n"
        f"  Test    : {analysis.affected_test}\n"
        f"  Category: {analysis.category} - {analysis.category_label}\n"
        f"  Flaky   : {analysis.is_flaky}\n"
        f"  Summary : {analysis.root_cause_summary[:120]}...\n"
        f"  Fix     : {analysis.suggested_fix[:120]}...\n"
        f"{'='*60}"
    )
    if not args.dry_run:
        report_failure(
            client=client,
            analysis=analysis,
            run_id=run_id,
            test_suite=test_suite,
            pr_number=args.pr,
        )


def _result_to_dict(analysis, run_id) -> dict:
    return {
        "run_id": run_id,
        "test": analysis.affected_test,
        "file": analysis.affected_file,
        "is_flaky": analysis.is_flaky,
        "category": analysis.category,
        "category_label": analysis.category_label,
        "confidence": analysis.confidence,
        "root_cause": analysis.root_cause_summary,
        "suggested_fix": analysis.suggested_fix,
    }


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(run(args))
