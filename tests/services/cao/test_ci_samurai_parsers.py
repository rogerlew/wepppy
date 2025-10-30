import importlib.util
import types
from pathlib import Path

import pytest


def load_module(path: str) -> types.ModuleType:
    p = Path(path)
    spec = importlib.util.spec_from_file_location(p.stem, p)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


@pytest.mark.unit
def test_parse_pytest_log_basic(tmp_path: Path):
    mod = load_module("services/cao/ci-samurai/parse_pytest_log.py")

    sample = """
============================= test session starts ==============================
collected 3 items

tests/foo/test_bar.py::test_ok PASSED                                     [ 33%]
FAILED tests/foo/test_bar.py::test_baz - AssertionError: boom
ERROR  tests/foo/test_bar.py::test_err - FileNotFoundError: missing
========================= 1 failed, 1 error in 0.12s ==========================
""".strip().splitlines(True)

    items = list(mod.iter_failures(sample))
    assert len(items) == 2
    assert items[0]["kind"] == "failed"
    assert items[0]["test"] == "tests/foo/test_bar.py::test_baz"
    assert "AssertionError" in items[0]["error"]
    assert items[1]["kind"] == "error"


@pytest.mark.unit
def test_parse_result_and_patch():
    mod = load_module("services/cao/ci-samurai/run_fixer_loop.py")
    output = """
Some preliminary output...
RESULT_JSON
```json
{"action":"pr","confidence":"high","primary_test":"tests/foo/test_bar.py::test_baz","handled_tests":["tests/foo/test_bar.py::test_baz"],"pr":{"branch":"ci/fix/2025-10-30/test_baz","title":"Fix: test_baz","body":"..."}}
```

PATCH
```patch
diff --git a/tests/foo/test_bar.py b/tests/foo/test_bar.py
index 1111111..2222222 100644
--- a/tests/foo/test_bar.py
+++ b/tests/foo/test_bar.py
@@
-assert 0
+assert 1
```
"""
    rj, pt = mod.parse_result_and_patch(output)
    assert rj is not None
    assert rj.get("action") == "pr"
    assert "tests/foo/test_bar.py::test_baz" in rj.get("handled_tests", [])
    assert pt is not None
    assert "diff --git a/tests/foo/test_bar.py" in pt


@pytest.mark.unit
def test_read_snippet(tmp_path: Path):
    mod = load_module("services/cao/ci-samurai/run_fixer_loop.py")
    test_file = tmp_path / "tests" / "foo" / "test_bar.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join([f"line {i}" for i in range(1, 301)])
    test_file.write_text(content)
    nodeid = f"{test_file.as_posix()}::test_baz"
    snippet = mod.read_snippet(tmp_path, nodeid, max_lines=10)
    assert snippet.splitlines()[0] == "line 1"
    assert len(snippet.splitlines()) == 10


@pytest.mark.unit
def test_validate_tests(monkeypatch):
    mod = load_module("services/cao/ci-samurai/run_fixer_loop.py")

    class DummyProc:
        def __init__(self, code: int):
            self.returncode = code
            self.stdout = ""
            self.stderr = ""

    calls = []

    def fake_ssh(host: str, cmd: str):
        calls.append((host, cmd))
        # Return success for a specific test, fail for others
        return DummyProc(0 if "tests/foo/test_bar.py::test_baz" in cmd else 1)

    monkeypatch.setattr(mod, "ssh", fake_ssh)
    res = mod.validate_tests("nuc2.local", "/workdir/wepppy", [
        "tests/foo/test_bar.py::test_baz",
        "tests/foo/test_bar.py::test_err",
    ])
    assert res["tests/foo/test_bar.py::test_baz"] is True
    assert res["tests/foo/test_bar.py::test_err"] is False
    # Ensure ssh called twice
    assert len(calls) == 2
