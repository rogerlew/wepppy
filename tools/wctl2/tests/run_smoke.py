from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from types import SimpleNamespace

from ._typer import CliRunner, TYPER_AVAILABLE

if TYPER_AVAILABLE:
    from tools.wctl2.__main__ import app, run
else:  # pragma: no cover - dependency missing
    app = run = None  # type: ignore[assignment]


class _StreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.status_code = 200
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def __enter__(self) -> "_StreamResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _JSONResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _DummyResult:
    returncode = 0


def main() -> None:
    runner = CliRunner()
    project_dir = Path(__file__).resolve().parents[3]

    from tools.wctl2.commands import passthrough, playback

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        if stream:
            return _StreamResponse(["smoke-line"])
        return _JSONResponse({"status": "ok", "url": url, "payload": json})

    def fake_run_compose(context, args, check=True):
        return _DummyResult()

    original_post = playback.requests.post
    original_run_compose = passthrough.run_compose
    playback.requests.post = fake_post  # type: ignore[assignment]
    passthrough.run_compose = fake_run_compose  # type: ignore[assignment]
    try:
        results = [
            runner.invoke(app, ["--project-dir", str(project_dir), "run-npm", "--help"]),
            runner.invoke(
                app,
                ["--project-dir", str(project_dir), "run-test-profile", "backed-globule", "--dry-run"],
            ),
            runner.invoke(
                app,
                ["--project-dir", str(project_dir), "run-fork-profile", "backed-globule", "--timeout", "120"],
            ),
            runner.invoke(
                app,
                [
                    "--project-dir",
                    str(project_dir),
                    "run-archive-profile",
                    "backed-globule",
                    "--archive-comment",
                    "smoke",
                ],
            ),
        ]
        original_argv = sys.argv
        sys.argv = ["wctl2", "--project-dir", str(project_dir), "docker", "compose", "config", "--help"]
        try:
            try:
                run()
            except SystemExit as exc:
                code = exc.code
            else:
                code = 0
        finally:
            sys.argv = original_argv

        results.append(SimpleNamespace(exit_code=code, stdout="", stderr=""))
    finally:
        playback.requests.post = original_post  # type: ignore[assignment]
        passthrough.run_compose = original_run_compose  # type: ignore[assignment]

    failures = [result for result in results if result.exit_code != 0]
    if failures:
        for failure in failures:
            print(failure.stdout)
            print(failure.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
