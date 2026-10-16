import json
from pathlib import Path

import pytest

from tools import check_test_isolation as cti

pytestmark = pytest.mark.unit


class _Report:
    nodeid = "tests/example.py::test_example"
    when = "call"
    failed = False
    skipped = False


def test_recorder_accepts_passing_pytest9_report_without_wasxfail() -> None:
    recorder = cti.RecorderPlugin()

    recorder.pytest_runtest_logreport(_Report())

    assert recorder.failures == []
    assert recorder.skips == []
    assert recorder.xfails == []


def test_module_diff_flags_stub_pollution() -> None:
    before = {
        "wepppy.real_module": {
            "name": "wepppy.real_module",
            "file": "/tmp/wepppy/real_module.py",
            "has_file": True,
            "is_package": False,
            "is_stub": False,
            "loader": "SourceFileLoader",
            "module_id": 1,
        }
    }
    after = {
        **before,
        "wepppy.fake_stub": {
            "name": "wepppy.fake_stub",
            "file": None,
            "has_file": False,
            "is_package": False,
            "is_stub": True,
            "loader": None,
            "module_id": 2,
        },
    }

    diff = cti.module_diff(before, after)
    assert diff.suspicious, "Stub module should be flagged as suspicious pollution"
    suspect = diff.suspicious[0]
    assert suspect.name == "wepppy.fake_stub"
    assert "sys.modules stub" in suspect.reason


def test_env_diff_highlights_changes() -> None:
    before = {"PATH": "/usr/bin", "WEPP_ENV": "one"}
    after = {"PATH": "/usr/bin", "WEPP_ENV": "two", "NEW_VAR": "set"}

    diff = cti.diff_env(before, after)
    assert diff.added == {"NEW_VAR": "set"}
    assert diff.changed == {"WEPP_ENV": ("one", "two")}
    assert diff.removed == {}


def test_singleton_diff_traces_growth() -> None:
    before = {"wepppy.nodb.base": {"_instances": 0}}
    after = {"wepppy.nodb.base": {"_instances": 1}}

    diff = cti.diff_singletons(before, after)
    assert diff.entries
    entry = diff.entries[0]
    assert entry.module == "wepppy.nodb.base"
    assert entry.attribute == "_instances"
    assert entry.before == 0
    assert entry.after == 1


def test_encode_decode_state_diff_roundtrip() -> None:
    diff = cti.StateDiff(
        modules=cti.ModuleDiff(
            added=[
                cti.ModuleRecord(
                    name="wepppy.fake",
                    file=None,
                    has_file=False,
                    is_package=False,
                    is_stub=True,
                    loader=None,
                    reason="example",
                )
            ]
        ),
        env=cti.EnvDiff(added={"A": "1"}),
        singletons=cti.SingletonDiff(entries=[cti.SingletonDiffEntry("m", "_instances", 0, 1)]),
        filesystem=cti.FileSystemDiff(created_files=["tmp.txt"], created_dirs=[]),
    )

    payload = cti.encode_state_diff(diff)
    decoded = cti._decode_state_diff(payload)
    assert decoded is not None
    assert decoded.modules is not None
    assert decoded.modules.added[0].name == "wepppy.fake"
    assert decoded.env and decoded.env.added["A"] == "1"
    assert decoded.singletons and decoded.singletons.entries[0].after == 1
    assert decoded.filesystem and decoded.filesystem.created_files == ["tmp.txt"]


def test_baseline_parsing(tmp_path: Path) -> None:
    baseline_data = {"suppressions": ["order-failure|42", "pollution|module|tests/file|wepppy.fake"]}
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline_data))

    baseline = cti.Baseline.from_path(baseline_path)
    assert not baseline.allows("order-failure|42")
    assert baseline.allows("order-failure|123")


def test_diff_filesystem_created_paths() -> None:
    before_files = {"one.txt"}
    before_dirs = {"a/"}
    after_files = {"one.txt", "two.txt"}
    after_dirs = {"a/", "b/"}

    diff = cti.diff_filesystem(before_files, before_dirs, after_files, after_dirs)
    assert diff.created_files == ["two.txt"]
    assert diff.created_dirs == ["b/"]


def test_worker_entry_writes_error_payload(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    result_path = tmp_path / "result.json"
    config_path.write_text(json.dumps({"targets": []}))

    def boom(config):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cti, "run_pytest_worker", boom)

    exit_code = cti.worker_entry(str(config_path), str(result_path))
    assert exit_code == cti.ExitCode.TOOL_ERROR.value

    payload = json.loads(result_path.read_text())
    assert payload["exit_code"] == cti.ExitCode.TOOL_ERROR.value
    assert payload["errors"][0]["nodeid"] == "<worker-exception>"
    assert "kaboom" in payload["errors"][0]["longrepr"]


def test_snapshots_do_not_resolve_lazy_attributes(monkeypatch):
    import sys
    import types

    lazy = types.ModuleType("wepppy.lazy_probe")
    def forbidden(name):
        raise AssertionError(f"observer resolved lazy attribute {name}")
    lazy.__getattr__ = forbidden
    lazy._cache = {"key": 1}
    monkeypatch.setitem(sys.modules, lazy.__name__, lazy)
    monkeypatch.setitem(sys.modules, "wepppy.blocked_probe", None)
    assert cti.create_module_snapshot()[lazy.__name__]["is_stub"]
    assert cti.capture_singleton_snapshot()[lazy.__name__] == {"_cache": 1}


def test_normal_import_is_not_pollution_but_replacement_is():
    record = cti.ModuleRecord("normal", "/normal.py", True, False, False,
                              "SourceFileLoader", "import")
    outcome = cti.PytestOutcome(exit_code=0, state_diff=cti.StateDiff(
        modules=cti.ModuleDiff(added=[record])))
    result = cti.FileIsolationResult("test.py", outcome)
    assert cti.summarize_pollution([result]) == []
    outcome.state_diff.modules.replaced.append(record)
    assert cti.summarize_pollution([result])


def test_identical_worker_errors_cannot_be_clean():
    outcome = cti.PytestOutcome(exit_code=2, errors=[cti.FailureEntry(
        "<worker-exception>", "internal", "snapshot failed")])
    runs = [cti.RandomRunResult(seed, "module", outcome) for seed in (42, 123)]
    issues = cti.summarize_random_runs(runs, verbose=False)
    assert len(issues) == 2
    assert issues[0].details["errors"][0]["longrepr"] == "snapshot failed"
    assert cti.summarize_file_isolation([cti.FileIsolationResult("test.py", outcome)], {})


def test_nonzero_file_exit_without_reports_is_not_clean():
    outcome = cti.PytestOutcome(exit_code=2)
    assert cti.summarize_file_isolation([cti.FileIsolationResult("test.py", outcome)], {})


def test_import_defaults_are_bounded_to_new_real_dependency_imports():
    before = cti.StateSnapshot(modules={}, env={})
    after = cti.StateSnapshot(modules={"pint": {"file": "/libs/pint/__init__.py", "module_id": 1}},
                              env={"PINT_ARRAY_PROTOCOL_FALLBACK": "0"})
    assert cti.compute_state_diff(before, after).env.is_empty()
    before.env = {"PINT_ARRAY_PROTOCOL_FALLBACK": "1"}
    assert cti.compute_state_diff(before, after).env.changed
    before.env = {}
    before.modules = after.modules
    assert cti.compute_state_diff(before, after).env.added


def test_worker_detects_collection_stub_and_env_leaks(tmp_path):
    target = tmp_path / "test_leak.py"
    target.write_text(
        "import os, sys, types\n"
        "sys.modules['isolation_collection_stub'] = types.ModuleType('isolation_collection_stub')\n"
        "os.environ['ISOLATION_COLLECTION_LEAK'] = 'yes'\n"
        "def test_pass(): pass\n"
    )
    outcome = cti.subprocess_run_worker({"targets": [str(target)], "enable_state_scan": True})
    assert outcome.exit_code == 0
    assert any(m.name == "isolation_collection_stub" for m in outcome.state_diff.modules.suspicious)
    assert outcome.state_diff.env.added["ISOLATION_COLLECTION_LEAK"] == "yes"
    assert "PYTEST_VERSION" not in outcome.state_diff.env.removed


def test_worker_clean_pytest_lifecycle_has_no_pollution(tmp_path, monkeypatch):
    # Model the CLI worker launch, without the parent test runner's active item.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    target = tmp_path / "test_clean.py"
    target.write_text("def test_pass(): pass\n")
    outcome = cti.subprocess_run_worker({"targets": [str(target)], "enable_state_scan": True})
    assert outcome.exit_code == 0
    assert cti.summarize_pollution([cti.FileIsolationResult(str(target), outcome)]) == []


def test_orchestrate_worker_errors_are_unsuppressible(monkeypatch, tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"suppressions": ["run-failure|0", "run-failure|1"]}))
    monkeypatch.setattr(cti, "discover_random_plugin", lambda *a, **k: None)
    monkeypatch.setattr(cti, "discover_json_report_plugin", lambda **k: False)
    monkeypatch.setattr(cti, "load_config_toml", lambda *a, **k: {})
    monkeypatch.setattr(cti, "subprocess_run_worker", lambda config: cti.PytestOutcome(
        exit_code=2, errors=[cti.FailureEntry("<worker-exception>", "internal", "broken")]))
    args = cti.parse_args(["--iterations", "2", "--baseline", str(baseline)])
    assert cti.orchestrate(args) == cti.ExitCode.TOOL_ERROR.value
    assert "No isolation issues detected" not in capsys.readouterr().out
    args.allow_failures = True
    assert cti.orchestrate(args) == cti.ExitCode.CLEAN.value
    assert "failed (exit 2)" in capsys.readouterr().out


def test_native_support_inventory_does_not_hide_replacements():
    import types
    native = types.ModuleType("cython_runtime")
    assert cti.classify_module(native)[2] is False
    fake = types.ModuleType("unrecognized_stub")
    assert cti.classify_module(fake)[2] is True
    before = {"cython_runtime": dict(file=None, has_file=False, is_package=False,
                                    is_stub=False, loader=None, module_id=1)}
    after = {"cython_runtime": dict(before["cython_runtime"], module_id=2)}
    diff = cti.module_diff(before, after)
    result = cti.FileIsolationResult("test.py", cti.PytestOutcome(
        exit_code=0, state_diff=cti.StateDiff(modules=diff)))
    assert cti.summarize_pollution([result])


@pytest.mark.parametrize("iterations", ["0", "-1"])
def test_zero_work_iterations_are_rejected(iterations):
    with pytest.raises(SystemExit) as exc:
        cti.parse_args(["--iterations", iterations])
    assert exc.value.code == 2


def test_native_support_shapes_reject_bare_named_stubs():
    import types
    for name in ("_openssl", "_cython_3_2_4", "swig_runtime_data4", "duckdb.duckdb.typing"):
        assert cti.classify_module(types.ModuleType(name))[2] is True


@pytest.mark.parametrize("dependency,key,value", [
    ("threadpoolctl", "KMP_DUPLICATE_LIB_OK", "True"),
    ("sklearn", "KMP_DUPLICATE_LIB_OK", "True"),
    ("fiona", "GDAL_CURL_CA_BUNDLE", "/libs/certifi/cacert.pem"),
    ("fiona", "PROJ_CURL_CA_BUNDLE", "/libs/certifi/cacert.pem"),
    ("pyogrio", "GDAL_CURL_CA_BUNDLE", "/libs/certifi/cacert.pem"),
    ("pyogrio", "PROJ_CURL_CA_BUNDLE", "/libs/certifi/cacert.pem"),
])
def test_additional_import_defaults_preserve_mutation_detection(dependency, key, value):
    modules = {name: {"file": f"/libs/{name}/__init__.py", "module_id": i}
               for i, name in enumerate((dependency, "certifi"))}
    before = cti.StateSnapshot(modules={}, env={})
    after = cti.StateSnapshot(modules=modules, env={key: value})
    assert cti.compute_state_diff(before, after).env.is_empty()
    before.modules = modules
    assert cti.compute_state_diff(before, after).env.added == {key: value}
    before.modules = {}
    before.env = {key: "existing"}
    assert cti.compute_state_diff(before, after).env.changed == {key: ("existing", value)}


def test_real_lazy_dependency_proxies_are_not_stubs():
    import sys
    import types
    import cython
    import passlib.utils.compat
    import passlib.hash

    for name in ("cython.parallel", "cython.cimports", "cython.cimports.libc",
                 "cython.dataclasses", "passlib.hash", "passlib.utils.compat"):
        assert not cti.classify_module(sys.modules[name])[2]
        assert cti.classify_module(types.ModuleType(name))[2]
