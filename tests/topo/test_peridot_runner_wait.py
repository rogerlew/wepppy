import threading
import time

import pytest

from wepppy.topo.peridot import peridot_runner


@pytest.mark.unit
def test_run_peridot_waits_for_subwta_arc(tmp_path, monkeypatch):
    wd = str(tmp_path)
    subwta_dir = tmp_path / "dem" / "topaz"
    subwta_dir.mkdir(parents=True)
    subwta_arc = subwta_dir / "SUBWTA.ARC"

    monkeypatch.setenv("PERIDOT_INPUT_WAIT_S", "1.0")

    called = {}

    class DummyProc:
        def wait(self):
            called["wait"] = True

    def dummy_popen(cmd, stdout=None, stderr=None):
        called["cmd"] = cmd
        return DummyProc()

    monkeypatch.setattr(peridot_runner, "_get_bin", lambda: "/fake/bin/abstract_watershed")
    monkeypatch.setattr(peridot_runner, "Popen", dummy_popen)

    def delayed_write():
        time.sleep(0.1)
        subwta_arc.write_text("ok", encoding="utf-8")

    thread = threading.Thread(target=delayed_write, daemon=True)
    thread.start()

    peridot_runner.run_peridot_abstract_watershed(
        wd,
        clip_hillslopes=False,
        verbose=False,
    )
    thread.join(timeout=1.0)

    assert "cmd" in called
    assert called.get("wait") is True


@pytest.mark.unit
def test_wait_for_file_times_out(tmp_path):
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        peridot_runner._wait_for_file(str(missing), timeout_s=0.1, poll_s=0.02)

