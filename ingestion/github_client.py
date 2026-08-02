import io
import logging
import zipfile
import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
PODMAN_REPO = "containers/podman"


class GitHubClient:
    """Wrapper around GitHub REST API for workflow metadata, logs, and issues."""

    def __init__(self, token: str, repo: str = PODMAN_REPO) -> None:
        self.repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._base = f"{GITHUB_API_BASE}/repos/{repo}"

    def get_workflow_run(self, run_id: int) -> dict:
        url = f"{self._base}/actions/runs/{run_id}"
        resp = httpx.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_workflow_run_attempts(self, run_id: int) -> list[dict]:
        """Fetch all attempt objects for a run ID."""
        url = f"{self._base}/actions/runs/{run_id}/attempts"
        attempts = []
        for attempt_number in range(1, 10):
            a_url = f"{self._base}/actions/runs/{run_id}/attempts/{attempt_number}"
            resp = httpx.get(a_url, headers=self._headers, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            attempts.append(resp.json())
        return attempts

    def get_jobs_for_run(self, run_id: int, attempt: int = 1) -> list[dict]:
        url = f"{self._base}/actions/runs/{run_id}/attempts/{attempt}/jobs"
        resp = httpx.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("jobs", [])

    def get_job_log(self, job_id: int) -> str:
        url = f"{self._base}/actions/jobs/{job_id}/logs"
        resp = httpx.get(url, headers=self._headers, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        return resp.text

    def download_run_logs_zip(self, run_id: int) -> dict[str, str]:
        """Download zip logs for a run and unpack them into a filename -> content dict."""
        url = f"{self._base}/actions/runs/{run_id}/logs"
        resp = httpx.get(url, headers=self._headers, timeout=120, follow_redirects=True)
        resp.raise_for_status()

        logs: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                with zf.open(name) as f:
                    logs[name] = f.read().decode("utf-8", errors="replace")
        return logs

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict:
        url = f"{self._base}/issues"
        payload = {"title": title, "body": body, "labels": labels}
        resp = httpx.post(url, headers=self._headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def update_issue(self, issue_number: int, body: str) -> dict:
        url = f"{self._base}/issues/{issue_number}"
        resp = httpx.patch(url, headers=self._headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def add_issue_comment(self, issue_number: int, body: str) -> dict:
        url = f"{self._base}/issues/{issue_number}/comments"
        resp = httpx.post(url, headers=self._headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_pr_review_comment(
        self, pr_number: int, body: str, commit_id: str, path: str, line: int
    ) -> dict:
        url = f"{self._base}/pulls/{pr_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": line,
        }
        resp = httpx.post(url, headers=self._headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_pr_comment(self, pr_number: int, body: str) -> dict:
        url = f"{self._base}/issues/{pr_number}/comments"
        resp = httpx.post(url, headers=self._headers, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_issues(self, query: str) -> list[dict]:
        url = f"{GITHUB_API_BASE}/search/issues"
        resp = httpx.get(
            url,
            headers=self._headers,
            params={"q": query, "per_page": 10},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
