from __future__ import annotations

import io
from pathlib import Path
import threading

import pytest

from tools import run_pytest_sharded as shard_runner

pytestmark = pytest.mark.unit


def test_strip_remainder_separator() -> None:
    assert shard_runner._strip_remainder_separator(["--", "tests", "-k", "foo"]) == [
        "tests",
        "-k",
        "foo",
    ]
    assert shard_runner._strip_remainder_separator(["tests"]) == ["tests"]


def test_contains_xdist_options_detects_supported_variants() -> None:
    assert shard_runner._contains_xdist_options(["-n", "4"])
    assert shard_runner._contains_xdist_options(["-nauto"])
    assert shard_runner._contains_xdist_options(["--numprocesses=2"])
    assert shard_runner._contains_xdist_options(["--dist=loadscope"])
    assert shard_runner._contains_xdist_options(["--tx", "popen"])
    assert not shard_runner._contains_xdist_options(["tests", "-k", "nodb"])


def test_plan_shards_is_deterministic_and_balanced(tmp_path: Path) -> None:
    files = []
    for name, size in (
        ("test_a.py", 100),
        ("test_b.py", 200),
        ("test_c.py", 300),
        ("test_d.py", 400),
    ):
        path = tmp_path / name
        path.write_bytes(b"x" * size)
        files.append(str(path))

    first = shard_runner.plan_shards(files=files, workers=2)
    second = shard_runner.plan_shards(files=files, workers=2)

    assert first == second
    assert len(first) == 2
    assert sorted(path for shard in first for path in shard) == sorted(files)

    totals = [sum((Path(path).stat().st_size for path in shard)) for shard in first]
    assert abs(totals[0] - totals[1]) <= 200


def test_plan_shards_prefers_timing_data_when_available(tmp_path: Path) -> None:
    fast_large = tmp_path / "test_fast_large.py"
    slow_small = tmp_path / "test_slow_small.py"
    medium_large = tmp_path / "test_medium_large.py"
    fast_large.write_bytes(b"x" * 10_000)
    slow_small.write_bytes(b"x" * 100)
    medium_large.write_bytes(b"x" * 8_000)

    files = [str(fast_large), str(slow_small), str(medium_large)]
    module_timings = {
        str(slow_small.resolve()): 25.0,
        str(fast_large.resolve()): 1.0,
        str(medium_large.resolve()): 1.0,
    }
    shards = shard_runner.plan_shards(files=files, workers=2, module_timings=module_timings)

    assert len(shards) == 2
    assert any(
        [shard_runner._normalize_path(path) for path in shard] == [str(slow_small.resolve())]
        for shard in shards
    )


def test_timing_cache_roundtrip_and_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_path = tmp_path / "timings.json"
    monkeypatch.setattr(shard_runner, "TIMING_CACHE_FILE", cache_path)

    module_a = str((tmp_path / "tests" / "test_a.py").resolve())
    module_b = str((tmp_path / "tests" / "test_b.py").resolve())

    shard_runner.save_module_timing_cache({module_a: 10.0})
    loaded = shard_runner.load_module_timing_cache()
    assert loaded[module_a] == pytest.approx(10.0)

    merged = shard_runner.merge_module_timings(loaded, {module_a: 20.0, module_b: 5.0}, alpha=0.5)
    shard_runner.save_module_timing_cache(merged)
    reloaded = shard_runner.load_module_timing_cache()

    assert reloaded[module_a] == pytest.approx(15.0)
    assert reloaded[module_b] == pytest.approx(5.0)


def test_split_pytest_options_and_targets_parses_common_flags() -> None:
    options, targets = shard_runner.split_pytest_options_and_targets(
        [
            "-q",
            "--maxfail=1",
            "-k",
            "openapi",
            "tests/microservices",
            "tests/tools/test_run_pytest_sharded.py::test_strip_remainder_separator",
        ]
    )
    assert options == ["-q", "--maxfail=1", "-k", "openapi"]
    assert targets == [
        "tests/microservices",
        "tests/tools/test_run_pytest_sharded.py::test_strip_remainder_separator",
    ]


def test_build_worker_pytest_args_prefers_targeted_nodeids(tmp_path: Path) -> None:
    test_file_a = tmp_path / "test_a.py"
    test_file_b = tmp_path / "test_b.py"
    test_file_a.write_text("def test_a():\n    assert True\n")
    test_file_b.write_text("def test_b():\n    assert True\n")

    options = ["-q", "-k", "test_a"]
    original_targets = [
        f"{test_file_a}::test_a",
        f"{test_file_b}::test_b",
    ]
    shard_files = [str(test_file_b)]
    worker_args = shard_runner.build_worker_pytest_args(
        options,
        original_targets,
        shard_files,
        basetemp_dir=str(tmp_path / "basetemp"),
    )
    assert "-q" in worker_args
    assert f"{test_file_b}::test_b" in worker_args
    assert f"{test_file_a}::test_a" not in worker_args


def test_stream_pipe_writes_stderr_channel(capsys: pytest.CaptureFixture[str]) -> None:
    lock = threading.Lock()
    shard_runner._stream_pipe(
        io.StringIO("hello from err\n"),
        shard_index=2,
        stream_name="stderr",
        print_lock=lock,
    )
    captured = capsys.readouterr()
    assert "[pytest-shard 2][stderr] hello from err" in captured.err
    assert "[pytest-shard 2][stderr] hello from err" not in captured.out


def test_aggregate_worker_summaries_rolls_up_totals_and_failures() -> None:
    summaries = [
        shard_runner.WorkerSummary(
            exit_code=1,
            collected=9,
            passed=5,
            failed=1,
            errors=1,
            skipped=2,
            warnings=3,
            module_durations={"tests/a.py": 12.5},
            failed_nodeids=["tests/a.py::test_fail"],
            error_nodeids=["tests/b.py::test_setup_error"],
        ),
        shard_runner.WorkerSummary(
            exit_code=0,
            collected=8,
            passed=7,
            failed=0,
            errors=0,
            skipped=1,
            warnings=2,
            module_durations={"tests/c.py": 4.0},
            failed_nodeids=[],
            error_nodeids=[],
        ),
    ]

    aggregate = shard_runner.aggregate_worker_summaries(summaries)

    assert aggregate.shards == 2
    assert aggregate.total_tests == 17
    assert aggregate.skipped == 3
    assert aggregate.warnings == 5
    assert aggregate.failures == 2
    assert aggregate.failed_nodeids == [
        "tests/a.py::test_fail",
        "tests/b.py::test_setup_error",
    ]


def test_aggregate_worker_summaries_deduplicates_failure_nodeids() -> None:
    summaries = [
        shard_runner.WorkerSummary(
            exit_code=1,
            collected=1,
            failed=1,
            errors=1,
            failed_nodeids=["tests/a.py::test_fail"],
            error_nodeids=["tests/a.py::test_fail"],
        )
    ]
    aggregate = shard_runner.aggregate_worker_summaries(summaries)
    assert aggregate.total_tests == 1
    assert aggregate.failures == 1
    assert aggregate.failed_nodeids == ["tests/a.py::test_fail"]


def test_should_update_timing_cache_requires_clean_run() -> None:
    clean = shard_runner.AggregateSummary(
        shards=2,
        total_tests=10,
        passed=10,
        skipped=0,
        warnings=0,
        failures=0,
        failed_nodeids=[],
    )
    dirty = shard_runner.AggregateSummary(
        shards=2,
        total_tests=10,
        passed=9,
        skipped=0,
        warnings=0,
        failures=1,
        failed_nodeids=["tests/a.py::test_fail"],
    )
    assert shard_runner.should_update_timing_cache(0, clean)
    assert not shard_runner.should_update_timing_cache(1, clean)
    assert not shard_runner.should_update_timing_cache(0, dirty)


def test_normalize_worker_exit_code_allows_empty_shards() -> None:
    empty = shard_runner.WorkerSummary(exit_code=5, collected=0)
    with_tests = shard_runner.WorkerSummary(exit_code=5, collected=3)
    assert shard_runner.normalize_worker_exit_code(5, empty) == 0
    assert shard_runner.normalize_worker_exit_code(5, with_tests) == 5
    assert shard_runner.normalize_worker_exit_code(1, empty) == 1
