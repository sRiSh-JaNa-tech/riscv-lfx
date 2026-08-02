import pytest
from unittest.mock import MagicMock

from reporter.deduplicator import compute_signature, find_existing_issue, _normalize_error


class TestNormalizeError:
    def test_strips_hex_addresses(self):
        raw = "panic at 0xdeadbeef00 in goroutine"
        result = _normalize_error(raw)
        assert "0xdeadbeef00" not in result

    def test_strips_iso_timestamps(self):
        raw = "failed at 2025-07-31T14:22:01.123Z due to timeout"
        result = _normalize_error(raw)
        assert "2025-07-31" not in result

    def test_strips_pid(self):
        result = _normalize_error("process pid 98765 killed")
        assert "98765" not in result

    def test_strips_temp_paths(self):
        result = _normalize_error("lock file /tmp/podman-lock-abc123 not found")
        assert "/tmp/podman-lock-abc123" not in result

    def test_lowercases(self):
        result = _normalize_error("NETAVARK TIMEOUT")
        assert result == result.lower()

    def test_collapses_whitespace(self):
        result = _normalize_error("a    b   c")
        assert "  " not in result


class TestComputeSignature:
    def test_returns_64_char_hex(self):
        sig = compute_signature("ginkgo", "my test", "some error")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_same_inputs_same_signature(self):
        s1 = compute_signature("bats", "network connect", "netavark timeout")
        s2 = compute_signature("bats", "network connect", "netavark timeout")
        assert s1 == s2

    def test_different_test_names_different_signatures(self):
        s1 = compute_signature("bats", "test A", "same error")
        s2 = compute_signature("bats", "test B", "same error")
        assert s1 != s2

    def test_different_errors_different_signatures(self):
        s1 = compute_signature("bats", "same test", "error A")
        s2 = compute_signature("bats", "same test", "error B")
        assert s1 != s2

    def test_volatile_noise_does_not_change_signature(self):
        err1 = "failed at pid 1234 with address 0xdeadbeef"
        err2 = "failed at pid 9999 with address 0xcafebabe"
        s1 = compute_signature("ginkgo", "race test", err1)
        s2 = compute_signature("ginkgo", "race test", err2)
        assert s1 == s2


class TestFindExistingIssue:
    def _make_client(self, search_results: list[dict]) -> MagicMock:
        client = MagicMock()
        client.search_issues.return_value = search_results
        return client

    def test_returns_none_when_no_results(self):
        client = self._make_client([])
        result = find_existing_issue(client, "a" * 64)
        assert result is None

    def test_returns_first_result_when_found(self):
        issue = {"number": 42, "title": "Flaky test", "body": "flake-sig:aabbccdd0011"}
        client = self._make_client([issue])
        result = find_existing_issue(client, "aabbccdd0011" + "x" * 52)
        assert result is issue

    def test_calls_search_with_short_sig(self):
        client = self._make_client([])
        sig = "abcdef123456" + "0" * 52
        find_existing_issue(client, sig)
        call_args = client.search_issues.call_args[0][0]
        assert "abcdef123456" in call_args

    def test_search_query_includes_flaky_label(self):
        client = self._make_client([])
        find_existing_issue(client, "a" * 64)
        call_args = client.search_issues.call_args[0][0]
        assert "ci/flaky" in call_args
