
import asyncio
import json
import logging
import os
import re
import shutil
import time
from queue import Queue
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool


def _resolve_extended_mods_data_root() -> str:
    """Normalise EXTENDED_MODS_DATA for playback sandboxes."""
    override = os.environ.get("EXTENDED_MODS_DATA")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    candidates = (
        "/wc1/geodata/extended_mods_data",
        "/geodata/extended_mods_data",
    )
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    repo_locations = Path(__file__).resolve().parents[2] / "wepppy" / "nodb" / "mods" / "locations"
    return str(repo_locations)


_EXTENDED_MODS_DATA_ROOT = _resolve_extended_mods_data_root()
os.environ.setdefault("EXTENDED_MODS_DATA", _EXTENDED_MODS_DATA_ROOT)


from wepppy.nodb.base import clear_locks, NoDbBase
from wepppy.nodb.core import Ron
from wepppy.profile_recorder.playback import PlaybackSession
from wepppy.profile_coverage import load_settings_from_env
try:
    from coverage import Coverage
    from coverage.exceptions import CoverageException
except ImportError as exc:  # coverage is required for profile tracing
    raise RuntimeError("coverage.py must be installed for profile coverage") from exc

PROFILE_ROOT = Path(os.environ.get("PROFILE_PLAYBACK_ROOT", "/workdir/wepppy-test-engine-data/profiles"))
# NOTE: WEPPcloud authentication cookies are flagged Secure, so playback must target HTTPS;
#       the default honours that requirement to avoid silent login failures on http://weppcloud:8000.
DEFAULT_BASE_URL = os.environ.get("PROFILE_PLAYBACK_BASE_URL", "https://wc.bearhive.duckdns.org/weppcloud")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
PROFILE_COVERAGE_SETTINGS = load_settings_from_env()
DEFAULT_COVERAGE_EXPORT_DIR = Path(
    os.environ.get("PROFILE_COVERAGE_EXPORT_DIR", "/tmp/profile-coverage")
)


def _sandbox_root(env_key: str, default_subdir: str) -> Path:
    base = Path(os.environ.get("PROFILE_PLAYBACK_BASE", "/workdir/wepppy-test-engine-data/playback"))
    return Path(os.environ.get(env_key, str(base / default_subdir)))


PLAYBACK_RUN_ROOT = _sandbox_root("PROFILE_PLAYBACK_RUN_ROOT", "runs")
PLAYBACK_FORK_ROOT = _sandbox_root("PROFILE_PLAYBACK_FORK_ROOT", "fork")
PLAYBACK_ARCHIVE_ROOT = _sandbox_root("PROFILE_PLAYBACK_ARCHIVE_ROOT", "archive")


class ProfileRunRequest(BaseModel):
    """Incoming payload for a profile replay request."""

    dry_run: bool = Field(False, description="Preview requests without executing them.")
    base_url: Optional[str] = Field(
        default=None,
        description="Override the target WEPPcloud base URL. Defaults to PROFILE_PLAYBACK_BASE_URL or http://weppcloud:8000/weppcloud.",
    )
    cookie: Optional[str] = Field(
        default=None,
        description="Optional Cookie header forwarded with every request to WEPPcloud.",
    )
    verbose: bool = Field(False, description="Emit progress logs during replay.")
    trace_code: bool = Field(False, description="Enable backend coverage tracing for the profile run.")
    coverage_dir: Optional[str] = Field(
        default=None,
        description="Directory (inside the profile-playback container) where combined coverage artifacts are mirrored.",
    )
    coverage_config: Optional[str] = Field(
        default=None,
        description="Optional path to coverage.profile-playback.ini overriding the default config file.",
    )


class ProfileRunResult(BaseModel):
    """Replay outcome returned to the caller."""

    profile: str
    run_id: str
    sandbox_run_id: Optional[str] = Field(
        default=None,
        description="Sandbox run identifier used for playback (profile;;tmp;;<uuid>).",
    )
    source_run_id: Optional[str] = Field(
        default=None,
        description="Original run identifier detected from the capture log.",
    )
    dry_run: bool
    base_url: str
    run_dir: str
    report: str
    requests: List[dict]
    coverage_artifact: Optional[str] = Field(
        default=None,
        description="Path to the combined profile coverage artifact when tracing is enabled.",
    )


class ProfileForkRequest(BaseModel):
    undisturbify: bool = Field(False, description="Request undisturbify processing during fork.")
    target_runid: Optional[str] = Field(
        default=None,
        description="Override the fork destination run id. Defaults to a generated profile prefix.",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Override the target WEPPcloud base URL. Defaults to PROFILE_PLAYBACK_BASE_URL or http://weppcloud:8000/weppcloud.",
    )
    cookie: Optional[str] = Field(
        default=None,
        description="Optional Cookie header forwarded with every request to WEPPcloud.",
    )
    timeout_seconds: int = Field(
        600,
        ge=1,
        le=3600,
        description="Seconds to wait for the fork RQ job to finish before timing out.",
    )


class ProfileForkResult(BaseModel):
    profile: str
    source_run_id: str
    sandbox_run_id: str
    new_run_id: str
    job_id: str
    status: str
    run_dir: str
    fork_dir: Optional[str]


class ProfileArchiveRequest(BaseModel):
    comment: Optional[str] = Field(
        default=None,
        description="Optional comment stored with the archive.",
        max_length=200,
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Override the target WEPPcloud base URL. Defaults to PROFILE_PLAYBACK_BASE_URL or http://weppcloud:8000/weppcloud.",
    )
    cookie: Optional[str] = Field(
        default=None,
        description="Optional Cookie header forwarded with every request to WEPPcloud.",
    )
    timeout_seconds: int = Field(
        600,
        ge=1,
        le=3600,
        description="Seconds to wait for the archive RQ job to finish before timing out.",
    )


class ProfileArchiveResult(BaseModel):
    profile: str
    run_id: str
    sandbox_run_id: str
    archive_run_id: str
    job_id: str
    status: str
    run_dir: str
    archive_dir: str
    archives: List[str]
    comment: Optional[str] = None


app = FastAPI(title="WEPPcloud Profile Playback", version="0.1.0")
_RUNNER_LOGGER = logging.getLogger("profile_playback.runner")
if PROFILE_COVERAGE_SETTINGS.enabled and Coverage is not None:
    PROFILE_COVERAGE_SETTINGS.ensure_data_root(_RUNNER_LOGGER)


def _resolve_config_path(override: Optional[str]) -> Optional[Path]:
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = (Path(__file__).resolve().parents[2] / override).resolve()
        candidate = candidate.expanduser()
        return candidate if candidate.exists() else None
    return PROFILE_COVERAGE_SETTINGS.config_path


def _combine_profile_coverage(slug: str, config_override: Optional[str], logger: logging.Logger) -> Optional[Path]:
    if not PROFILE_COVERAGE_SETTINGS.enabled:
        logger.debug("Profile coverage disabled; skipping combine for %s", slug)
        return None
    data_root = PROFILE_COVERAGE_SETTINGS.data_root
    shards = sorted(data_root.glob(f"{slug}.coverage.*"))
    if not shards:
        logger.warning("No coverage shards found for %s in %s", slug, data_root)
        return None

    target_file = data_root / f"{slug}.coverage"
    try:
        target_file.unlink(missing_ok=True)
    except OSError:
        pass

    config_path = _resolve_config_path(config_override)
    kwargs = {"data_file": str(target_file)}
    if config_path:
        kwargs["config_file"] = str(config_path)

    try:
        coverage_runner = Coverage(**kwargs)
        coverage_runner.combine([str(path) for path in shards])
        coverage_runner.save()
    except CoverageException as exc:
        logger.error("Failed to combine coverage for %s: %s", slug, exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Unexpected coverage error for %s: %s", slug, exc)
        return None

    return target_file


def _export_profile_coverage(slug: str, output_dir: Optional[str], config_override: Optional[str], logger: logging.Logger) -> Optional[Path]:
    combined = _combine_profile_coverage(slug, config_override, logger)
    if combined is None:
        return None

    destination_root = Path(output_dir).expanduser() if output_dir else DEFAULT_COVERAGE_EXPORT_DIR
    try:
        destination_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Unable to create coverage export directory %s: %s", destination_root, exc)
        return None

    target = destination_root / combined.name
    try:
        shutil.copy2(combined, target)
    except OSError as exc:
        logger.error("Failed to copy coverage artifact for %s to %s: %s", slug, target, exc)
        return None

    return target


def _color_output_enabled() -> bool:
    override = os.environ.get("PROFILE_PLAYBACK_COLOR")
    if override is not None:
        return override.lower() not in {"0", "false", "no", "off"}
    return os.environ.get("NO_COLOR") is None


_COLOR_OUTPUT = _color_output_enabled()


class _PlaybackLogFormatter(logging.Formatter):
    """Formatter that injects ANSI colour codes into playback logs."""

    _RESET = "\033[0m"
    _MAGENTA = "\033[95m"
    _GREEN = "\033[92m"
    _RED = "\033[91m"
    _YELLOW = "\033[93m"
    _DODGER_BLUE2 = "\033[38;5;27m"
    _PURPLE3 = "\033[38;5;99m"

    _HTTP_STATUS_PATTERN = re.compile(r"HTTP (\d{3})")
    _URL_PATTERN = re.compile(r"https?://[^\s]+")
    _JOB_PATTERN = re.compile(r"\bjob ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)
    _DURATION_PATTERN = re.compile(r"\((\d+)ms\)")
    _SECONDS_PATTERN = re.compile(r"\b\d+\.\d{3}s\b")

    def __init__(self, colorize: bool = True) -> None:
        super().__init__("%(asctime)s [profile_playback] %(levelname)s %(message)s")
        self._colorize = colorize

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        if not self._colorize:
            return rendered
        return self._apply_colours(rendered)

    def _wrap(self, text: str, colour: str) -> str:
        return f"{colour}{text}{self._RESET}"

    def _apply_colours(self, text: str) -> str:
        text = self._colour_prefix(text)
        text = self._colour_job_tokens(text)
        text = self._colour_http_status(text)
        text = self._colour_durations(text)
        text = self._colour_seconds(text)
        text = self._colour_urls(text)
        text = self._colour_json_blocks(text)
        return text

    def _colour_prefix(self, text: str) -> str:
        tag_token = " [profile_playback]"
        idx = text.find(tag_token)
        if idx == -1:
            return text
        timestamp = text[:idx]
        remainder = text[idx:]
        coloured_timestamp = self._wrap(timestamp, self._MAGENTA)
        coloured_remainder = remainder.replace("[profile_playback]", self._wrap("[profile_playback]", self._MAGENTA), 1)
        return f"{coloured_timestamp}{coloured_remainder}"

    def _colour_http_status(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            code = match.group(1)
            colour = self._GREEN if code.startswith("2") else self._RED
            return self._wrap(f"HTTP {code}", colour)

        return self._HTTP_STATUS_PATTERN.sub(repl, text)

    def _colour_job_tokens(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            job_token = match.group(0)
            return self._wrap(job_token, self._PURPLE3)

        return self._JOB_PATTERN.sub(repl, text)

    def _colour_durations(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            raw_value = match.group(1)
            try:
                value = int(raw_value)
            except ValueError:
                return match.group(0)
            if value < 400:
                colour = self._GREEN
            elif value < 1000:
                colour = self._YELLOW
            else:
                colour = self._RED
            return self._wrap(match.group(0), colour)

        return self._DURATION_PATTERN.sub(repl, text)

    def _colour_seconds(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            return self._wrap(match.group(0), self._PURPLE3)

        return self._SECONDS_PATTERN.sub(repl, text)

    def _colour_urls(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            url = match.group(0)
            # Avoid colouring trailing punctuation that is not part of the URL.
            stripped = url.rstrip(").,]}>\"'")
            suffix = url[len(stripped):]
            return f"{self._wrap(stripped, self._DODGER_BLUE2)}{suffix}"

        return self._URL_PATTERN.sub(repl, text)

    def _colour_json_blocks(self, text: str) -> str:
        lines = text.splitlines()
        if len(lines) == 1 and "{" not in text:
            return text

        coloured_lines: List[str] = []
        inside_json = False
        brace_balance = 0

        for line in lines:
            new_line = line
            stripped = line.lstrip()
            starts_json = stripped.startswith(("{", "[", '"'))
            if inside_json or "response preview" in line or starts_json:
                if not inside_json:
                    brace_index = line.find("{")
                    if brace_index != -1:
                        prefix = line[:brace_index]
                        suffix = line[brace_index:]
                        new_line = prefix + self._wrap(suffix, self._GREEN)
                        brace_balance = suffix.count("{") - suffix.count("}")
                        inside_json = brace_balance > 0
                    else:
                        new_line = self._wrap(line, self._GREEN)
                        brace_balance = line.count("{") - line.count("}")
                        inside_json = brace_balance > 0
                else:
                    new_line = self._wrap(line, self._GREEN)
                    brace_balance += line.count("{") - line.count("}")
                    inside_json = brace_balance > 0

            if brace_balance <= 0:
                brace_balance = 0
                inside_json = False

            coloured_lines.append(new_line)

        return "\n".join(coloured_lines)


if not _RUNNER_LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(_PlaybackLogFormatter(colorize=_COLOR_OUTPUT))
    _RUNNER_LOGGER.addHandler(handler)
_RUNNER_LOGGER.setLevel(logging.INFO)
_RUNNER_LOGGER.propagate = False


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


class _QueueLogHandler(logging.Handler):
    def __init__(self, queue: Queue) -> None:
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple queue push
        msg = self.format(record)
        self.queue.put(msg)


def _results_root() -> Path:
    root = PROFILE_ROOT / "_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _store_result(token: str, payload: ProfileRunResult) -> Path:
    path = _results_root() / f"{token}.json"
    path.write_text(json.dumps(payload.model_dump(), indent=2), encoding="utf-8")
    return path


class ProfileOperationError(RuntimeError):
    """Raised when profile playback helper operations fail."""


def _normalize_base_url(value: Optional[str]) -> str:
    base = value or DEFAULT_BASE_URL
    return base.rstrip("/")


def _detect_profile_run_id(profile_root: Path) -> str:
    events_path = profile_root / "capture" / "events.jsonl"
    if not events_path.exists():
        raise ProfileOperationError(f"Capture log not found: {events_path}")

    with events_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProfileOperationError(f"Invalid capture entry: {line}") from exc
            if event.get("stage") != "request":
                continue
            endpoint = str(event.get("endpoint", ""))
            path = PlaybackSession._normalise_path(endpoint)  # reuse helper
            parts = [segment for segment in path.split("/") if segment]
            if "runs" in parts:
                idx = parts.index("runs")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    raise ProfileOperationError("Unable to determine run id from capture events.")


def _prepare_sandbox_run(profile_root: Path, run_id: str) -> tuple[str, Path]:
    source_run_dir = profile_root / "run"
    if not source_run_dir.exists():
        raise ProfileOperationError(f"Profile run snapshot missing: {source_run_dir}")

    sandbox_uuid = uuid4().hex
    PLAYBACK_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    sandbox_run_dir = PLAYBACK_RUN_ROOT / sandbox_uuid

    shutil.rmtree(sandbox_run_dir, ignore_errors=True)
    sandbox_run_dir.mkdir(parents=True, exist_ok=True)

    config_candidates = [
        source_run_dir / "config",
        profile_root / "capture" / "seed" / "config",
    ]

    selected_config_dir: Optional[Path] = None
    config_files: List[Path] = []
    active_config_slug: Optional[str] = None

    for candidate in config_candidates:
        if not candidate.is_dir():
            continue
        cfgs = sorted(candidate.glob("*.cfg"))
        if not cfgs:
            continue
        selected_config_dir = candidate
        config_files = cfgs
        active_marker = candidate / "active_config.txt"
        if active_marker.exists():
            try:
                active_text = active_marker.read_text(encoding="utf-8").strip()
            except OSError as exc:
                _RUNNER_LOGGER.warning("Unable to read active config marker %s: %s", active_marker, exc)
            else:
                if active_text:
                    active_config_slug = Path(active_text).stem
        break

    if selected_config_dir:
        available_config_slugs = sorted(cfg.stem for cfg in config_files)
        if not available_config_slugs:
            raise ProfileOperationError(
                f"Profile seed config missing .cfg files in {selected_config_dir}"
            )
        if active_config_slug and active_config_slug not in available_config_slugs:
            raise ProfileOperationError(
                "Profile seed active_config.txt references "
                f"'{active_config_slug}.cfg' but only {available_config_slugs} exist"
            )

        for item in sorted(selected_config_dir.iterdir()):
            if item.name == "active_config.txt":
                continue
            target_path = sandbox_run_dir / item.name
            if item.is_dir():
                shutil.copytree(item, target_path, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target_path)

        config_slug = active_config_slug or available_config_slugs[0]

        try:
            (sandbox_run_dir / "active_config.txt").write_text(config_slug, encoding="utf-8")
        except OSError as exc:
            _RUNNER_LOGGER.warning("Unable to write active config marker for %s: %s", sandbox_run_dir, exc)

        config_path = sandbox_run_dir / f"{config_slug}.cfg"
        if not config_path.exists():
            raise ProfileOperationError(
                f"Profile seed config failed to copy {config_slug}.cfg into sandbox {sandbox_run_dir}"
            )

        Ron(str(sandbox_run_dir), f"{config_slug}.cfg", run_group="profile", group_name="tmp")
    else:
        # Fallback: profile lacks usable config seeds; clone the recorded run snapshot
        shutil.rmtree(sandbox_run_dir, ignore_errors=True)
        shutil.copytree(source_run_dir, sandbox_run_dir)
        _RUNNER_LOGGER.warning(
            "Profile %s missing config seeds; using snapshot copy for playback",
            profile_root,
        )

    return sandbox_uuid, sandbox_run_dir


def _prepare_sandbox_clone(profile_root: Path, run_id: str) -> tuple[str, Path]:
    source_run_dir = profile_root / "run"
    if not source_run_dir.exists():
        raise ProfileOperationError(f"Profile run snapshot missing: {source_run_dir}")

    sandbox_uuid = uuid4().hex
    PLAYBACK_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    sandbox_run_dir = PLAYBACK_RUN_ROOT / sandbox_uuid

    shutil.rmtree(sandbox_run_dir, ignore_errors=True)

    try:
        shutil.copytree(source_run_dir, sandbox_run_dir)
    except OSError as exc:
        raise ProfileOperationError(f"Failed to clone profile run snapshot: {exc}") from exc

    return sandbox_uuid, sandbox_run_dir


def _clear_sandbox_locks(runid: str, logger: logging.Logger, extra_runids: Optional[List[str]] = None) -> None:
    targets = {runid}
    if extra_runids:
        targets.update(extra_runids)
    try:
        total_cleared = 0
        for candidate in targets:
            cleared = clear_locks(candidate)
            total_cleared += len(cleared)
            if cleared:
                logger.info("Cleared %d lock(s) for %s", len(cleared), candidate)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Unable to clear locks for %s: %s", ", ".join(sorted(targets)), exc)
        return
    if total_cleared == 0:
        logger.info("No locks cleared for %s", ", ".join(sorted(targets)))


def _read_active_config(run_dir: Path) -> str:
    config_path = run_dir / "active_config.txt"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8").strip()
        if content:
            return content
    return "cfg"


def _ensure_session(base_url: str, cookie: Optional[str], *, logger: logging.Logger) -> requests.Session:
    session = requests.Session()
    login_base_url = base_url.rstrip("/")
    if cookie:
        session.headers.update({"Cookie": cookie})
    else:
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            raise ProfileOperationError("ADMIN_EMAIL and ADMIN_PASSWORD must be configured for playback authentication")
        logger.info("Authenticating playback session against %s", login_base_url)
        try:
            _perform_login(session, login_base_url, ADMIN_EMAIL, ADMIN_PASSWORD)
        except Exception as exc:
            raise ProfileOperationError(f"Login failed: {exc}") from exc
        _log_auth_success("playback", login_base_url)
        _mirror_cookies(session, login_base_url, base_url)
    return session


def _poll_job_completion(
    session: requests.Session,
    base_url: str,
    job_id: str,
    timeout_seconds: int,
    *,
    logger: logging.Logger,
    interval: float = 2.0,
) -> Dict[str, object]:
    if not job_id:
        raise ProfileOperationError("Fork/archive response did not include a job identifier")

    jobinfo_url = f"{base_url.rstrip('/')}/rq/api/jobinfo/{job_id}"
    deadline = time.monotonic() + timeout_seconds
    last_payload: Dict[str, object] = {}
    while True:
        response = session.get(jobinfo_url, timeout=60)
        response.raise_for_status()
        payload = response.json()
        last_payload = payload
        status = str(payload.get("status", "unknown")).lower()
        if status in {"finished", "failed", "stopped"}:
            return payload
        if time.monotonic() >= deadline:
            raise ProfileOperationError(
                f"Job {job_id} did not finish within {timeout_seconds}s (last status: {status})"
            )
        logger.debug("Job %s status=%s; polling again in %.1fs", job_id, status, interval)
        time.sleep(interval)


def fork_profile(profile: str, payload: ProfileForkRequest, logger: Optional[logging.Logger] = None) -> ProfileForkResult:
    log = logger or _RUNNER_LOGGER
    profile_root = PROFILE_ROOT / profile
    if not profile_root.exists():
        raise ProfileOperationError(f"Profile not found: {profile_root}")

    run_id = _detect_profile_run_id(profile_root)
    sandbox_uuid, sandbox_run_dir = _prepare_sandbox_clone(profile_root, run_id)
    sandbox_run_id = f"profile;;tmp;;{sandbox_uuid}"
    _clear_sandbox_locks(sandbox_run_id, log, extra_runids=[run_id])

    base_url = _normalize_base_url(payload.base_url)
    session = _ensure_session(base_url, payload.cookie, logger=log)
    config_slug = _read_active_config(sandbox_run_dir)

    fork_uuid = uuid4().hex
    target_runid = payload.target_runid or f"profile;;fork;;{fork_uuid}"
    fork_url = f"{base_url}/runs/{sandbox_run_id}/{config_slug}/rq/api/fork"
    form_data = {
        "undisturbify": "true" if payload.undisturbify else "false",
        "target_runid": target_runid,
    }

    log.info("Submitting fork job for profile=%s run=%s -> %s", profile, sandbox_run_id, target_runid)
    response = session.post(fork_url, data=form_data, timeout=payload.timeout_seconds)
    response.raise_for_status()
    body = response.json()
    if not body.get("Success"):
        raise ProfileOperationError(body.get("Error") or "Fork request failed")

    job_id = body.get("job_id")
    new_run_id = body.get("new_runid") or target_runid
    job_info = _poll_job_completion(session, base_url, job_id, payload.timeout_seconds, logger=log)

    fork_identifier = new_run_id or target_runid
    fork_suffix = fork_identifier.split(";;")[-1]
    PLAYBACK_FORK_ROOT.mkdir(parents=True, exist_ok=True)
    fork_dir = PLAYBACK_FORK_ROOT / fork_suffix

    return ProfileForkResult(
        profile=profile,
        source_run_id=run_id,
        sandbox_run_id=sandbox_run_id,
        new_run_id=new_run_id,
        job_id=job_id,
        status=str(job_info.get("status", "unknown")),
        run_dir=str(sandbox_run_dir),
        fork_dir=str(fork_dir),
    )


def archive_profile(profile: str, payload: ProfileArchiveRequest, logger: Optional[logging.Logger] = None) -> ProfileArchiveResult:
    log = logger or _RUNNER_LOGGER
    profile_root = PROFILE_ROOT / profile
    if not profile_root.exists():
        raise ProfileOperationError(f"Profile not found: {profile_root}")

    run_id = _detect_profile_run_id(profile_root)
    sandbox_uuid, sandbox_run_dir = _prepare_sandbox_clone(profile_root, run_id)
    sandbox_run_id = f"profile;;tmp;;{sandbox_uuid}"
    _clear_sandbox_locks(sandbox_run_id, log, extra_runids=[run_id])

    archive_uuid = uuid4().hex
    archive_run_id = f"profile;;archive;;{archive_uuid}"

    base_url = _normalize_base_url(payload.base_url)
    session = _ensure_session(base_url, payload.cookie, logger=log)
    config_slug = _read_active_config(sandbox_run_dir)

    archive_url = f"{base_url}/runs/{sandbox_run_id}/{config_slug}/rq/api/archive"
    body_payload: Dict[str, object] = {}
    if payload.comment is not None:
        body_payload["comment"] = payload.comment

    log.info("Submitting archive job for profile=%s run=%s", profile, sandbox_run_id)
    response = session.post(archive_url, json=body_payload, timeout=payload.timeout_seconds)
    response.raise_for_status()
    body = response.json()
    if not body.get("Success"):
        raise ProfileOperationError(body.get("Error") or "Archive request failed")

    job_id = body.get("job_id")
    job_info = _poll_job_completion(session, base_url, job_id, payload.timeout_seconds, logger=log)

    archives_dir = sandbox_run_dir / "archives"
    archive_target = PLAYBACK_ARCHIVE_ROOT / archive_uuid
    archive_target.parent.mkdir(parents=True, exist_ok=True)
    if archive_target.exists():
        shutil.rmtree(archive_target)
    archives: List[str] = []
    if archives_dir.exists():
        shutil.copytree(archives_dir, archive_target)
        archives = sorted(p.name for p in archive_target.iterdir())
    else:
        archive_target.mkdir(parents=True, exist_ok=True)

    return ProfileArchiveResult(
        profile=profile,
        run_id=run_id,
        sandbox_run_id=sandbox_run_id,
    archive_run_id=archive_run_id,
        job_id=job_id,
        status=str(job_info.get("status", "unknown")),
        run_dir=str(sandbox_run_dir),
        archive_dir=str(archive_target),
        archives=archives,
        comment=payload.comment,
    )


async def _stream_run_result(token: str, queue: Queue, worker_future) -> StreamingResponse:
    async def generator():
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, queue.get)
            if line is None:
                break
            yield (line + "\n").encode("utf-8")
        await worker_future

    return StreamingResponse(generator(), media_type="text/plain")


@app.post("/run/{profile}")
async def run_profile(profile: str, payload: ProfileRunRequest) -> StreamingResponse:
    profile_root = PROFILE_ROOT / profile
    if not profile_root.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_root}")

    # Detect run ID and prepare clean sandbox
    try:
        run_id = _detect_profile_run_id(profile_root)
    except ProfileOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Clean up any existing sandbox. The playback session itself will clear
    # locks at the appropriate stages, so we avoid doing it twice here.
    try:
        sandbox_uuid, sandbox_run_dir = _prepare_sandbox_run(profile_root, run_id)
    except ProfileOperationError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to prepare sandbox: {exc}") from exc

    sandbox_run_id = f"profile;;tmp;;{sandbox_uuid}"

    login_base_url = (payload.base_url or DEFAULT_BASE_URL).rstrip("/")
    playback_base_url = login_base_url

    session = requests.Session()
    if payload.cookie:
        session.headers.update({"Cookie": payload.cookie})
    elif not payload.dry_run:
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            raise HTTPException(status_code=500, detail="ADMIN_EMAIL/ADMIN_PASSWORD must be configured for playback authentication")
        try:
            _RUNNER_LOGGER.info("Authenticating playback session for %s", profile)
            _perform_login(session, login_base_url, ADMIN_EMAIL, ADMIN_PASSWORD)
        except Exception as exc:
            _RUNNER_LOGGER.exception("Playback authentication failed for %s", profile)
            raise HTTPException(status_code=502, detail=f"Login failed: {exc}") from exc
        else:
            _log_auth_success(profile, login_base_url)
            _mirror_cookies(session, login_base_url, playback_base_url)

    if payload.trace_code:
        session.headers["X-Profile-Trace"] = profile

    _RUNNER_LOGGER.info("Starting playback for %s (dry_run=%s)", profile, payload.dry_run)

    log_queue: Queue[str | None] = Queue()
    session_token = uuid4().hex

    def playback_worker() -> None:
        session_logger = logging.getLogger(f"profile_playback.session.{session_token}")
        session_logger.setLevel(logging.INFO)
        session_logger.propagate = False

        handler = _QueueLogHandler(log_queue)
        handler.setFormatter(_PlaybackLogFormatter(colorize=_COLOR_OUTPUT))
        session_logger.addHandler(handler)

        coverage_artifact: Optional[Path] = None
        try:
            playback = PlaybackSession(
                profile_root=profile_root,
                base_url=playback_base_url,
                execute=not payload.dry_run,
                run_dir=sandbox_run_dir,  # Use pre-cleaned sandbox
                session=session,
                verbose=True,
                logger=session_logger,
                playback_run_id=sandbox_run_id,
            )
            playback.run()
            if payload.trace_code:
                coverage_artifact = _export_profile_coverage(
                    profile,
                    payload.coverage_dir,
                    payload.coverage_config,
                    session_logger,
                )
                if coverage_artifact:
                    session_logger.info("Profile coverage saved to %s", coverage_artifact)
                else:
                    session_logger.warning(
                        "Profile coverage requested for %s but no artifact was generated.",
                        profile,
                    )
            request_log = [{"id": request_id, "status": status} for request_id, status in playback.results]
            result = ProfileRunResult(
                profile=profile,
                run_id=getattr(playback, "run_id", profile),
                sandbox_run_id=getattr(playback, "playback_run_id", sandbox_run_id),
                source_run_id=getattr(playback, "original_run_id", run_id),
                dry_run=payload.dry_run,
                base_url=playback_base_url,
                run_dir=str(playback.run_dir),
                report=playback.report(),
                requests=request_log,
                coverage_artifact=str(coverage_artifact) if coverage_artifact else None,
            )
            result_path = _store_result(session_token, result)
            session_logger.info("result token=%s stored at %s", session_token, result_path)
        except Exception:  # pragma: no cover - defensive logging
            session_logger.exception("Playback error token=%s", session_token)
        finally:
            # Clean up NoDb instances to release file descriptors
            if sandbox_run_dir is not None:
                try:
                    cleaned = NoDbBase.cleanup_run_instances(str(sandbox_run_dir))
                    if cleaned > 0:
                        session_logger.debug("Cleaned up %d NoDb instances for %s", cleaned, sandbox_run_dir)
                except Exception as cleanup_exc:
                    session_logger.warning("Error cleaning up NoDb instances: %s", cleanup_exc)
            log_queue.put(None)
            session_logger.removeHandler(handler)
            handler.close()

    loop = asyncio.get_running_loop()
    worker_future = loop.run_in_executor(None, playback_worker)
    return await _stream_run_result(session_token, log_queue, worker_future)


@app.get("/run/result/{token}", response_model=ProfileRunResult)
async def run_result(token: str) -> ProfileRunResult:
    path = _results_root() / f"{token}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Result not found for token {token}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProfileRunResult(**data)


@app.post("/fork/{profile}", response_model=ProfileForkResult)
async def fork_profile_route(profile: str, payload: ProfileForkRequest) -> ProfileForkResult:
    try:
        return await run_in_threadpool(fork_profile, profile, payload, _RUNNER_LOGGER)
    except ProfileOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/archive/{profile}", response_model=ProfileArchiveResult)
async def archive_profile_route(profile: str, payload: ProfileArchiveRequest) -> ProfileArchiveResult:
    try:
        return await run_in_threadpool(archive_profile, profile, payload, _RUNNER_LOGGER)
    except ProfileOperationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



def _perform_login(session: requests.Session, base_url: str, email: str, password: str) -> None:
    login_url = f"{base_url.rstrip('/')}/login"
    response = session.get(login_url, timeout=30)
    response.raise_for_status()
    token = _extract_csrf_token(response.text)
    payload = {
        "email": email,
        "password": password,
        "remember": "y",
        "csrf_token": token or "",
        "next": "",
    }
    post = session.post(login_url, data=payload, timeout=30, allow_redirects=False)
    if post.status_code not in (200, 302, 303):
        raise RuntimeError(f"HTTP {post.status_code}")
    if "session" not in session.cookies:
        raise RuntimeError(f"session cookie missing after login (cookies={session.cookies.get_dict()})")


def _log_auth_success(profile: str, base_url: str) -> None:
    import logging

    logger = logging.getLogger("profile_playback")
    logger.info("Authenticated playback for profile %s against %s", profile, base_url)


def _mirror_cookies(session: requests.Session, source_base: str, target_base: str) -> None:
    from urllib.parse import urlparse

    if not target_base:
        return

    source_host = urlparse(source_base).hostname if source_base else None
    target_host = urlparse(target_base).hostname if target_base else None

    if not source_host or not target_host or source_host == target_host:
        return

    for name in ("session", "remember_token"):
        value = session.cookies.get(name, domain=source_host)
        if value:
            session.cookies.set(name, value, domain=target_host, path="/")


def _extract_csrf_token(html: str) -> Optional[str]:
    import re

    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if match:
        return match.group(1)
    return None


if __name__ == "__main__":
    import uvicorn


    uvicorn.run("services.profile_playback.app:app", host="0.0.0.0", port=8070, reload=False)
try:
    from coverage import Coverage, CoverageException
except ImportError:
    Coverage = None  # type: ignore[assignment]
    CoverageException = Exception  # type: ignore[assignment]
