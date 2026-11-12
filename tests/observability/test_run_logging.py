"""Real file/queue boundaries for the run-scoped descriptor lifetime."""
import io
import logging
from logging.handlers import QueueListener
from concurrent.futures import ThreadPoolExecutor
import queue
import shutil

import pytest

from wepppy.observability.run_logging import RunFileHandler
from wepppy.observability.safe_traceback import UNAVAILABLE

pytestmark = pytest.mark.unit


def record(message):
    return logging.LogRecord("run-test", logging.INFO, __file__, 1, message, (), None)


def test_creation_append_unicode_and_threaded_writes(tmp_path):
    path = tmp_path / "run.log"
    path.write_text("previous\n")
    handler = RunFileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    assert handler.stream is None
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: handler.handle(record(f"café-{i}")), range(200)))
    assert handler.stream is None
    handler.close()
    lines = path.read_text().splitlines()
    assert lines[0] == "previous"
    assert sorted(lines[1:]) == sorted(f"INFO:café-{i}" for i in range(200))


def test_constructor_preserves_missing_parent_failure(tmp_path):
    with pytest.raises(FileNotFoundError):
        RunFileHandler(tmp_path / "absent" / "run.log")


def test_idle_handler_and_late_records_do_not_pin_or_recreate_directory(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    handler = RunFileHandler(run / "run.log")
    output = io.StringIO()
    other_sink = logging.StreamHandler(output)
    events = queue.Queue()
    listener = QueueListener(events, handler, other_sink)
    listener.start()
    try:
        events.put(record("first"))
        events.join()
        assert handler.stream is None
        shutil.rmtree(run)
        events.put(record("late-one"))
        events.put(record("late-two"))
        events.join()
        assert listener._thread.is_alive()
        assert output.getvalue() == "first\nlate-one\nlate-two\n"
        assert not run.exists()
        assert capsys.readouterr().err == (UNAVAILABLE + "\n") * 2
    finally:
        listener.stop()
        handler.close()


def test_write_failure_releases_stream_without_raw_arguments(tmp_path, monkeypatch, capsys):
    handler = RunFileHandler(tmp_path / "run.log")

    class BrokenStream(io.StringIO):
        def write(self, value):
            raise OSError("private diagnostic")

    stream = BrokenStream()
    monkeypatch.setattr(handler, "_open", lambda: stream)
    handler.handle(record("secret-canary"))
    assert stream.closed
    assert handler.stream is None
    assert capsys.readouterr().err == UNAVAILABLE + "\n"
