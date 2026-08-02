import pytest
from parsers.bats_parser import parse_bats_log, BATSFailure

SAMPLE_BATS_LOG = """\
1..10
ok 1 podman info
ok 2 podman version
not ok 3 podman network connect/disconnect
# (in test file /home/runner/work/podman/test/system/500-networking.bats, line 127)
#   `run_podman network connect mynet myctr' failed with status 1
# -- stderr --
# Error: netavark: timeout connecting to network after 5 seconds
# --
# output: 
ok 4 podman ps
not ok 5 podman pull from quay.io
# (in test file /home/runner/work/podman/test/system/010-images.bats, line 44)
#   `run_podman pull quay.io/libpod/busybox:latest' failed with status 1
# -- stderr --
# Error: initializing source docker://quay.io/libpod/busybox:latest: pinging container registry quay.io: Get "https://quay.io/v2/": dial tcp: i/o timeout
# --
ok 6 podman run hello-world
ok 7 podman rm
ok 8 podman rmi
ok 9 podman volume create
ok 10 podman system prune
"""

SAMPLE_BATS_PASSING = """\
1..5
ok 1 podman info
ok 2 podman version
ok 3 podman run
ok 4 podman ps
ok 5 podman rm
"""


class TestParseBatsLog:
    def test_returns_list(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert isinstance(result, list)

    def test_detects_two_failures(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert len(result) == 2

    def test_failure_type(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        for f in result:
            assert isinstance(f, BATSFailure)

    def test_first_failure_name(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert "network" in result[0].test_name.lower()

    def test_second_failure_name(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert "quay.io" in result[1].test_name.lower()

    def test_bats_file_extracted(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert result[0].bats_file.endswith(".bats")
        assert result[1].bats_file.endswith(".bats")

    def test_bats_line_extracted(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert result[0].bats_line == 127
        assert result[1].bats_line == 44

    def test_failed_command_extracted(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert "run_podman network connect" in result[0].failed_command

    def test_exit_status(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert result[0].exit_status == 1

    def test_diagnostic_output_contains_error(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert "netavark" in result[0].diagnostic_output.lower()

    def test_empty_log_returns_empty_list(self):
        assert parse_bats_log("") == []

    def test_passing_log_returns_empty_list(self):
        assert parse_bats_log(SAMPLE_BATS_PASSING) == []

    def test_framework_field(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        for f in result:
            assert f.framework == "bats"

    def test_test_index_correct(self):
        result = parse_bats_log(SAMPLE_BATS_LOG)
        assert result[0].test_index == 3
        assert result[1].test_index == 5
