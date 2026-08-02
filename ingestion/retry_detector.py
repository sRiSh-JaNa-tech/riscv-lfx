import logging
from dataclasses import dataclass

from .github_client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class RetryAnalysis:
    run_id: int
    total_attempts: int
    is_flaky: bool
    failed_attempt: int
    passed_attempt: int | None
    failed_job_ids: list[int]


def detect_flake(client: GitHubClient, run_id: int) -> RetryAnalysis:
    """Check if attempt 1 failed but a later attempt passed (flake vs hard failure)."""
    attempts = client.get_workflow_run_attempts(run_id)
    if not attempts:
        raise RuntimeError(f"No attempt data found for run_id={run_id}")

    failed_attempt_num: int | None = None
    passed_attempt_num: int | None = None

    for attempt in attempts:
        num = attempt["run_attempt"]
        conclusion = attempt.get("conclusion") or ""

        if conclusion == "failure" and failed_attempt_num is None:
            failed_attempt_num = num
        elif conclusion == "success" and failed_attempt_num is not None:
            passed_attempt_num = num
            break

    is_flaky = failed_attempt_num is not None and passed_attempt_num is not None

    if failed_attempt_num is None:
        logger.warning("run_id=%s has no failed attempt; all attempts passed.", run_id)
        failed_attempt_num = 1

    jobs = client.get_jobs_for_run(run_id, attempt=failed_attempt_num)
    failed_job_ids = [
        job["id"]
        for job in jobs
        if job.get("conclusion") == "failure"
    ]

    logger.info(
        "run_id=%s | attempts=%s | is_flaky=%s | failed_jobs=%s",
        run_id,
        len(attempts),
        is_flaky,
        failed_job_ids,
    )

    return RetryAnalysis(
        run_id=run_id,
        total_attempts=len(attempts),
        is_flaky=is_flaky,
        failed_attempt=failed_attempt_num,
        passed_attempt=passed_attempt_num,
        failed_job_ids=failed_job_ids,
    )
