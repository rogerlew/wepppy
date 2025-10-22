import json
from pathlib import Path

import pytest

from tools import check_test_isolation as cti

pytestmark = pytest.mark.unit

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
