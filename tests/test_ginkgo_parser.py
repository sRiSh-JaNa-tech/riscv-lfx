import pytest
from parsers.ginkgo_parser import parse_ginkgo_log, GinkgoFailure

SAMPLE_GINKGO_LOG = """\
Running Suite: Podman E2E Suite - /home/runner/work/podman
============================================================
Will run 1 of 42 specs
------------------------------
[FAILED] podman network connect should connect a container to a network after start
/home/runner/work/podman/test/e2e/network_test.go:127

Expected
    <string>: Error: netavark setup timeout after 5s
to equal
    <string>: 

In [It] at: /home/runner/work/podman/test/e2e/network_test.go:127 @ 14:23:01.123

goroutine 1 [running]:
github.com/containers/podman/test/e2e.init.func1()
	/home/runner/work/podman/test/e2e/network_test.go:45 +0x1234
------------------------------
Ran 1 of 42 Specs in 45.321s -- FAILED! -- 1 Failure
"""

SAMPLE_GINKGO_EMPTY = "All 42 specs passed!\nRan 42 of 42 Specs in 10.1s -- SUCCESS!"


class TestParseGinkgoLog:
    def test_returns_list(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        assert isinstance(result, list)

    def test_detects_failure_block(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        assert len(result) >= 1

    def test_failure_type(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        for f in result:
            assert isinstance(f, GinkgoFailure)

    def test_spec_name_extracted(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        assert any("network connect" in f.spec_name.lower() for f in result)

    def test_source_file_extracted(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        for f in result:
            if f.source_file:
                assert ".go" in f.source_file

    def test_source_line_positive(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        for f in result:
            assert f.source_line >= 0

    def test_empty_log_returns_empty_list(self):
        assert parse_ginkgo_log("") == []

    def test_passing_log_returns_empty_list(self):
        assert parse_ginkgo_log(SAMPLE_GINKGO_EMPTY) == []

    def test_framework_field(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        for f in result:
            assert f.framework == "ginkgo"

    def test_raw_block_capped(self):
        result = parse_ginkgo_log(SAMPLE_GINKGO_LOG)
        for f in result:
            assert len(f.raw_block) <= 4000
