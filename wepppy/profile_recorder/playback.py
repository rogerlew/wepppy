from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from contextlib import ExitStack
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

from wepppy.nodb.core.ron import Ron

Event = Dict[str, object]


class PlaybackSession:
    """
    Minimal playback runner that replays recorder events against a WEPPcloud instance.

    Only GET requests and JSON POST bodies are currently supported. Other payload
    types (form-data uploads) are surfaced in the report for manual follow-up.
    """

    def __init__(
        self,
        profile_root: Path,
        *,
        base_url: str,
        execute: bool = False,
        run_dir: Optional[Path] = None,
        session: Optional[requests.Session] = None,
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.profile_root = profile_root
        self.execute = execute
        self.base_url = base_url.rstrip("/")
        self.capture_dir = profile_root / "capture"
        self.profile_run_root = profile_root / "run"
        self.session = session or requests.Session()
        self.verbose = verbose
        self._logger = logger
        self._pending_jobs: deque[Tuple[str, str]] = deque()
        self.seed_root = profile_root / "capture" / "seed"
        self.seed_upload_root = self.seed_root / "uploads"
        self.seed_config_stem: Optional[str] = None

        if self.verbose:
            self._log(f"PlaybackSession created (execute={self.execute}, verbose={self.verbose})")

        if not self.capture_dir.exists():
            raise FileNotFoundError(f"Capture directory not found: {self.capture_dir}")

        self.events = self._load_events(self.capture_dir / "events.jsonl")
        self.run_id = self._detect_run_id(self.events) or profile_root.name
        self.original_run_id = self.run_id
        self.playback_run_id = f"profile;;tmp;;{self.original_run_id}"
        self._log(f"Loaded {len(self.events)} events from {self.capture_dir}")
        self._log(f"Resolved run id: {self.original_run_id}")
        self._log(f"Using playback run id: {self.playback_run_id}")

        if run_dir is not None:
            self.run_dir = run_dir
            self._log(f"Using existing run directory: {self.run_dir}")
        else:
            self.run_dir = self._prepare_run_directory(profile_root, self.run_id)
            self._log(f"Prepared clean playback workspace at: {self.run_dir}")

        self.requests = self._index_requests(self.events)
        self.results: List[Tuple[str, str]] = []

    def _prepare_run_directory(self, profile_root: Path, run_id: str) -> Path:
        playback_root = Path(os.environ.get("PROFILE_PLAYBACK_RUN_ROOT", "/workdir/wepppy-test-engine-data/playback_runs"))
        playback_root.mkdir(parents=True, exist_ok=True)
        target = playback_root / run_id
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        self._hydrate_seed_files(target)
        return target

    @staticmethod
    def _detect_run_id(events: Iterable[Event]) -> Optional[str]:
        for event in events:
            if event.get("stage") != "request":
                continue
            endpoint = str(event.get("endpoint", ""))
            path = PlaybackSession._normalise_path(endpoint)
            parts = [part for part in path.split("/") if part]
            if "runs" in parts:
                try:
                    idx = parts.index("runs")
                    return parts[idx + 1]
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _load_events(path: Path) -> List[Event]:
        events: List[Event] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        return events

    @staticmethod
    def _index_requests(events: Iterable[Event]) -> Dict[str, Event]:
        requests: Dict[str, Event] = {}
        for event in events:
            if event.get("stage") == "request" and "id" in event:
                requests[str(event["id"])] = event
        return requests

    def run(self) -> None:
        self._log("Beginning playback")
        for event in self.events:
            if event.get("stage") != "response":
                continue
            if event.get("ok") is False:
                continue
            request_id = str(event.get("id"))
            req = self.requests.get(request_id)
            if req is None:
                self.results.append((request_id, "skipped (missing request metadata)"))
                continue

            method = str(req.get("method", "GET")).upper()
            endpoint = str(req.get("endpoint", ""))
            path = self._normalise_path(endpoint)
            effective_path = self._remap_run_path(path)

            if method == "GET" and "/rq/api/jobstatus/" in effective_path:
                self.results.append((request_id, f"{effective_path}: skipped recorded jobstatus poll"))
                continue
            if method == "GET" and "/elevationquery/" in effective_path:
                self.results.append((request_id, f"{effective_path}: skipped recorded elevation query"))
                continue

            summary = req.get("requestMeta") or {}
            json_payload: Optional[dict] = None
            if isinstance(summary, dict) and summary.get("jsonPayload"):
                try:
                    json_payload = json.loads(summary["jsonPayload"])
                except json.JSONDecodeError:
                    self.results.append((request_id, f"{effective_path}: invalid JSON payload"))
                    continue

            if method not in ("GET", "POST"):
                self.results.append((request_id, f"{effective_path}: unsupported method {method}"))
                self._log(f"Skipping {request_id}: unsupported method {method}")
                continue

            expected_status = self._expected_status(event)
            params = self._extract_query_params(event)
            url = self._build_url(effective_path)

            if self.verbose:
                display_path = effective_path
                if effective_path != path:
                    display_path = f"{effective_path} (source {path})"
                msg = f"{request_id} {method} {url}"
                if display_path != effective_path:
                    msg += f" [{display_path}]"
                if params:
                    msg += f" params={dict(params)}"
                if json_payload is not None:
                    msg += " body=json"
                self._log(msg)

            if self.execute:
                if self._pending_jobs:
                    self._await_pending_jobs()
                try:
                    response = self._execute_request(
                        method,
                        url,
                        params,
                        json_payload,
                        expected_status,
                        effective_path,
                        summary,
                    )
                    self.results.append((request_id, f"{effective_path}: HTTP {response.status_code}"))
                    if self.verbose:
                        self._log(f"{request_id} → HTTP {response.status_code}")
                except requests.RequestException as exc:
                    self.results.append((request_id, f"{effective_path}: error {exc}"))
                    if self.verbose:
                        self._log(f"{request_id} → error {exc}")
            else:
                action = f"{method} {effective_path}"
                if json_payload is not None:
                    action += f" payload={json_payload}"
                self.results.append((request_id, f"dry-run {action}"))
        if self.execute:
            self._await_pending_jobs()

    @staticmethod
    def _normalise_path(endpoint: str) -> str:
        if not endpoint:
            return ""
        parsed = urlparse(endpoint)
        path = parsed.path or endpoint
        # Ensure path starts with single slash
        if not path.startswith("/"):
            path = "/" + path
        return path

    def report(self) -> str:
        lines = ["Playback results:"]
        for request_id, status in self.results:
            lines.append(f"  - {request_id}: {status}")
        lines.append(f"Playback run directory: {self.run_dir}")
        self._log("Playback complete")
        return "\n".join(lines)

    def _execute_request(
        self,
        method: str,
        url: str,
        params: List[Tuple[str, str]],
        json_payload: Optional[dict],
        expected_status: int,
        path: str,
        request_meta: Dict[str, Any],
    ) -> requests.Response:
        kwargs: Dict[str, object] = {"timeout": 60}
        files_stack = ExitStack()
        form_data: Dict[str, Any] = {}
        files_info: Dict[str, Tuple[Path, str]] = {}
        if params:
            kwargs["params"] = params
        if method == "POST":
            form_data, files_info = self._build_form_request(path, request_meta)
        if method == "POST" and json_payload is not None:
            kwargs["json"] = json_payload
        elif method == "POST" and request_meta.get("bodyType") == "form-data":
            if form_data:
                kwargs["data"] = form_data
            if files_info:
                prepared_files: Dict[str, Tuple[str, Any, str]] = {}
                for field, (file_path, mime) in files_info.items():
                    file_handle = files_stack.enter_context(open(file_path, "rb"))
                    prepared_files[field] = (os.path.basename(file_path), file_handle, mime)
                kwargs["files"] = prepared_files
            else:
                self.results.append(("form-data", f"{path}: missing upload payload"))
                files_stack.close()
                raise requests.RequestException("missing form-data payload")
        elif method == "POST" and form_data:
            kwargs["data"] = form_data

        if method == "POST" and json_payload is None and not form_data and not files_info and request_meta.get("bodyType") != "form-data":
            if self.verbose:
                self._log(f"{path}: unsupported payload type")
            self.results.append(("unsupported", f"{path}: unsupported payload type"))
            files_stack.close()
            raise requests.RequestException("unsupported payload type")

        try:
            response = self.session.request(method, url, **kwargs)
        finally:
            files_stack.close()

        if method == "POST" and self.execute:
            if self.verbose:
                self._log(f"{path} response content-type {response.headers.get('Content-Type', '')}")
                try:
                    preview = response.text[:200]
                except Exception:
                    preview = "<unavailable>"
                self._log(f"{path} response preview {preview}")
            job_id = self._extract_job_id(response)
            if job_id:
                if self.verbose:
                    self._log(f"job {job_id} enqueued by {path}")
                self._pending_jobs.append((job_id, path))
            elif self.verbose:
                self._log(f"no job id detected in {path} response")

        if self._should_wait_for_completion(method, path, expected_status):
            if self.verbose:
                self._log("waiting for task completion")
            return self._poll_for_completion(url, params, expected_status)

        return response

    def _poll_for_completion(
        self,
        url: str,
        params: List[Tuple[str, str]],
        expected_status: int,
        *,
        timeout: int = 300,
        interval: float = 2.0,
    ) -> requests.Response:
        end_time = time.time() + timeout
        last_response: Optional[requests.Response] = None
        last_status: Optional[int] = None
        attempt = 0
        while True:
            try:
                response = self.session.get(url, params=params or None, timeout=60)
            except requests.RequestException as exc:
                if last_response is not None:
                    return last_response
                raise exc

            last_response = response
            if response.status_code == expected_status:
                if self.verbose:
                    self._log("wait complete")
                return response
            if response.status_code not in (401, 403, 404):
                if self.verbose:
                    self._log(f"wait aborted on status {response.status_code}")
                return response
            if time.time() >= end_time:
                if self.verbose:
                    self._log(f"wait timed out after {attempt + 1} attempts (last status {response.status_code})")
                return response
            if self.verbose and (attempt == 0 or response.status_code != last_status):
                msg = f"waiting... status {response.status_code}"
                content_type = response.headers.get("Content-Type", "")
                if content_type.startswith("application/json"):
                    try:
                        msg += f" body={response.json()}"
                    except ValueError:
                        msg += " body=<invalid json>"
                else:
                    snippet = response.text[:300] if response.text else ""
                    if snippet:
                        msg += f" body={snippet}"
                self._log(msg)
            last_status = response.status_code
            attempt += 1
            time.sleep(interval)

    def _expected_status(self, event: Event) -> int:
        status = event.get("status")
        if isinstance(status, int):
            return status
        if event.get("ok") is True:
            return 200
        return 400

    def _extract_query_params(self, event: Event) -> List[Tuple[str, str]]:
        endpoint = str(event.get("endpoint") or "")
        parsed = urlparse(endpoint)
        if parsed.query:
            return parse_qsl(parsed.query, keep_blank_values=True)
        return []

    def _build_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        normalized_path = path.lstrip("/")
        if normalized_path.startswith("query-engine/") or normalized_path == "query-engine":
            origin = urljoin(f"{base}/", "/")
            return urljoin(origin, normalized_path)
        return urljoin(f"{base}/", normalized_path)

    def _should_wait_for_completion(self, method: str, path: str, expected_status: int) -> bool:
        if method != "GET" or expected_status != 200:
            return False
        return any(path.endswith(suffix) for suffix in _WAIT_SUFFIXES)

    def _log(self, message: str) -> None:
        if self._logger is not None:
            self._logger.info(message)
        else:
            print(f"[playback] {message}")

    def _await_pending_jobs(self) -> None:
        while self._pending_jobs:
            job_id, task_path = self._pending_jobs.popleft()
            if self.verbose:
                self._log(f"waiting for job {job_id} ({task_path}) to finish")
            self._wait_for_job(job_id, task=task_path)

    def _remap_run_path(self, path: str) -> str:
        prefix = f"/runs/{self.original_run_id}/"
        if path.startswith(prefix):
            return path.replace(prefix, f"/runs/{self.playback_run_id}/", 1)
        if path == f"/runs/{self.original_run_id}":
            return f"/runs/{self.playback_run_id}"
        return path

    def _build_form_request(
        self,
        path: str,
        request_meta: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Tuple[Path, str]]]:
        data: Dict[str, Any] = {}
        files: Dict[str, Tuple[Path, str]] = {}
        normalized = path.rstrip("/")

        try:
            if normalized.endswith("rq/api/build_landuse"):
                self._populate_landuse_form(data, files)
            elif normalized.endswith("rq/api/build_treatments"):
                self._populate_landuse_form(data, files)
            elif normalized.endswith("rq/api/build_soils"):
                self._populate_soils_form(data)
            elif normalized.endswith("tasks/upload_sbs"):
                self._populate_sbs_form(data, files)
            elif normalized.endswith("tasks/upload_cover_transform"):
                self._populate_cover_transform_form(files)
            elif normalized.endswith("tasks/upload_cli"):
                self._populate_cli_form(files)
            elif normalized.endswith("rq/api/run_ash"):
                self._populate_ash_form(data, files)
            elif normalized.endswith("rq/api/run_omni"):
                self._populate_omni_form(data, files)
        except Exception as exc:
            self._log(f"Failed to build form-data payload for {path}: {exc}")

        return data, files

    def _populate_soils_form(
        self,
        data: Dict[str, Any],
    ) -> None:
        from wepppy.nodb.core.soils import Soils

        soils = Soils.getInstance(self.run_dir)
        initial_sat = getattr(soils, "initial_sat", None)
        if initial_sat is not None:
            data["initial_sat"] = self._format_number(initial_sat)

        mods = getattr(soils, "mods", [])
        if "disturbed" in mods:
            try:
                from wepppy.nodb.mods.disturbed import Disturbed
                disturbed = Disturbed.getInstance(self.run_dir)
                sol_ver = getattr(disturbed, "sol_ver", None)
                if sol_ver is not None:
                    data["sol_ver"] = self._format_number(sol_ver)
            except Exception as exc:
                if self.verbose:
                    self._log(f"Failed to load Disturbed for soils form: {exc}")

    def _populate_landuse_form(
        self,
        data: Dict[str, Any],
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        from wepppy.nodb.core.landuse import Landuse, LanduseMode
        from wepppy.nodb.mods.disturbed import Disturbed

        landuse = Landuse.getInstance(self.run_dir)
        mode = int(landuse.mode)
        data["landuse_mode"] = str(mode)

        nlcd_db = getattr(landuse, "nlcd_db", None)
        if nlcd_db:
            data["landuse_db"] = str(nlcd_db)

        single_selection = getattr(landuse, "_single_selection", None)
        if single_selection is not None:
            data["landuse_single_selection"] = str(single_selection)

        mapping = landuse.mapping
        if mapping:
            data["landuse_management_mapping_selection"] = mapping

        if "disturbed" in landuse.mods:
            disturbed = Disturbed.getInstance(self.run_dir)
            burn_shrubs = getattr(disturbed, "burn_shrubs", False)
            burn_grass = getattr(disturbed, "burn_grass", False)
            data["checkbox_burn_shrubs"] = "true" if burn_shrubs else "false"
            data["checkbox_burn_grass"] = "true" if burn_grass else "false"

        upload_dir = self.seed_upload_root / "landuse"
        candidates = sorted(upload_dir.glob("input_upload_landuse*")) if upload_dir.exists() else []
        if not candidates:
            fallback = Path(self.run_dir) / "landuse" / "nlcd.tif"
            if fallback.exists():
                candidates = [fallback]
            else:
                snapshot = self.profile_run_root / "landuse" / "nlcd.tif"
                if snapshot.exists():
                    candidates = [snapshot]
        if candidates:
            files["input_upload_landuse"] = (candidates[0], "application/octet-stream")

    def _populate_sbs_form(
        self,
        data: Dict[str, Any],
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        upload_dir = self.seed_upload_root / "sbs"
        candidates = sorted(upload_dir.glob("input_upload_sbs*")) if upload_dir.exists() else []
        search_roots: List[Path] = []
        if not candidates:
            search_roots.extend([
                Path(self.run_dir) / "disturbed",
                Path(self.run_dir) / "baer",
                self.profile_run_root / "disturbed",
                self.profile_run_root / "baer",
            ])
            for root in search_roots:
                if root.is_dir():
                    for candidate in sorted(root.glob("*.tif")):
                        if candidate not in candidates:
                            candidates.append(candidate)
        if candidates:
            files["input_upload_sbs"] = (candidates[0], "application/octet-stream")

    def _populate_cover_transform_form(
        self,
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        upload_dir = self.seed_upload_root / "revegetation"
        candidates = sorted(upload_dir.glob("input_upload_cover_transform*")) if upload_dir.exists() else []
        if not candidates:
            fallback_root = self.profile_run_root / "revegetation"
            if fallback_root.exists():
                candidates = sorted(fallback_root.glob("*.csv"))
        if candidates:
            files["input_upload_cover_transform"] = (candidates[0], "text/csv")

    def _populate_cli_form(
        self,
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        upload_dir = self.seed_upload_root / "climate"
        candidates = sorted(upload_dir.glob("input_upload_cli*")) if upload_dir.exists() else []
        if not candidates:
            fallback_root = self.profile_run_root / "climate"
            if fallback_root.exists():
                candidates = sorted(fallback_root.glob("*.cli"))
        if candidates:
            files["input_upload_cli"] = (candidates[0], "text/plain")

    def _populate_ash_form(
        self,
        data: Dict[str, Any],
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        from wepppy.nodb.mods.ash_transport import Ash

        ash = Ash.getInstance(str(self.run_dir))
        mode = int(getattr(ash, "ash_depth_mode", 1))
        data["ash_depth_mode"] = str(mode)

        fire_date = getattr(ash, "fire_date", None)
        if fire_date is not None:
            formatted = self._format_yearless_date(fire_date)
            if formatted:
                data["fire_date"] = formatted

        # Always include current bulk densities so backend stays in sync.
        data["field_black_bulkdensity"] = self._format_number(getattr(ash, "field_black_ash_bulkdensity", 0.0))
        data["field_white_bulkdensity"] = self._format_number(getattr(ash, "field_white_ash_bulkdensity", 0.0))

        if mode == 0:
            data["ini_black_load"] = self._format_number(getattr(ash, "ini_black_ash_load", 0.0))
            data["ini_white_load"] = self._format_number(getattr(ash, "ini_white_ash_load", 0.0))
        elif mode == 1:
            data["ini_black_depth"] = self._format_number(getattr(ash, "ini_black_ash_depth_mm", 0.0))
            data["ini_white_depth"] = self._format_number(getattr(ash, "ini_white_ash_depth_mm", 0.0))

        if getattr(ash, "run_wind_transport", False):
            data["checkbox_run_wind_transport"] = "on"

        model = getattr(ash, "model", None)
        if model:
            data["ash_model"] = str(model)
            data["ash_model_select"] = str(model)

        transport_mode = getattr(ash, "transport_mode", None)
        if transport_mode:
            data["ash_transport_mode_select"] = str(transport_mode)

        upload_dir = self.seed_upload_root / "ash"
        seed_candidates = sorted(upload_dir.glob("input_upload_ash_load*")) if upload_dir.exists() else []
        if not seed_candidates:
            load_path = getattr(ash, "ash_load_fn", None)
            if load_path:
                load_candidate = Path(load_path)
                if load_candidate.exists():
                    seed_candidates = [load_candidate]
        if seed_candidates:
            files["input_upload_ash_load"] = (seed_candidates[0], "application/octet-stream")

        type_candidates = sorted(upload_dir.glob("input_upload_ash_type_map*")) if upload_dir.exists() else []
        if not type_candidates:
            type_path = getattr(ash, "ash_type_map_fn", None)
            if type_path:
                type_candidate = Path(type_path)
                if type_candidate.exists():
                    type_candidates = [type_candidate]
        if type_candidates:
            files["input_upload_ash_type_map"] = (type_candidates[0], "application/octet-stream")

    def _populate_omni_form(
        self,
        data: Dict[str, Any],
        files: Dict[str, Tuple[Path, str]],
    ) -> None:
        from wepppy.nodb.mods.omni import Omni

        omni = Omni.getInstance(str(self.run_dir))
        scenarios = list(getattr(omni, "scenarios", []))
        payload_defs: List[Dict[str, Any]] = []

        for idx, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                continue
            scenario_type = scenario.get("type")
            payload_def: Dict[str, Any] = {}
            for key, value in scenario.items():
                if key in {"sbs_file_path"}:
                    continue
                payload_def[key] = value

            if scenario_type == "sbs_map":
                original_path = scenario.get("sbs_file_path") or scenario.get("sbs_file")
                candidate = self._resolve_omni_sbs_seed(idx, original_path)
                if candidate is not None:
                    payload_def["sbs_file"] = candidate.name
                    files[f"scenarios[{idx}][sbs_file]"] = (candidate, "application/octet-stream")
                else:
                    self._log(f"Omni SBS scenario {idx} missing seed file; playback may fail")

            payload_defs.append(payload_def)

        if payload_defs:
            data["scenarios"] = json.dumps(payload_defs)

    def _hydrate_seed_files(self, target: Path) -> None:
        if not self.seed_root.exists():
            return
        config_seed = self.seed_root / "config"
        if config_seed.is_dir():
            active_marker = config_seed / "active_config.txt"
            if active_marker.exists():
                try:
                    active_text = active_marker.read_text(encoding="utf-8").strip()
                except Exception as exc:
                    self._log(f"Failed to read active config seed {active_marker}: {exc}")
                else:
                    if active_text:
                        self.seed_config_stem = Path(active_text).stem
            for item in config_seed.iterdir():
                if item.name == "active_config.txt":
                    continue
                if item.is_file():
                    try:
                        shutil.copy2(item, target / item.name)
                    except Exception as exc:
                        self._log(f"Failed to copy seed config {item}: {exc}")
        if self.seed_config_stem:
            try:
                Ron(str(target), f"{self.seed_config_stem}.cfg")
            except Exception as exc:
                self._log(f"Failed to initialize Ron with seed config {self.seed_config_stem}: {exc}")

    def _format_yearless_date(self, value: Any) -> Optional[str]:
        try:
            month = getattr(value, "month", None)
            day = getattr(value, "day", None)
            if month is not None and day is not None:
                return f"{int(month)}/{int(day)}"
        except Exception:
            pass
        try:
            return str(value)
        except Exception:
            return None

    def _format_number(self, value: Any) -> str:
        try:
            numeric = float(value)
        except Exception:
            return str(value)
        return f"{numeric:.6g}"

    def _resolve_omni_sbs_seed(self, idx: int, original_path: Optional[str]) -> Optional[Path]:
        candidates: List[Path] = []
        seed_dir = self.seed_upload_root / "omni" / "_limbo"
        if seed_dir.exists():
            candidates.extend(sorted(seed_dir.rglob("*")))

        if original_path:
            original_name = Path(original_path).name
            for candidate in candidates:
                if candidate.is_file() and candidate.name == original_name:
                    return candidate

        if not candidates:
            fallback = self.profile_run_root / "omni" / "_limbo"
            if fallback.exists():
                for candidate in sorted(fallback.rglob("*")):
                    if candidate.is_file():
                        candidates.append(candidate)

        if original_path:
            original_name = Path(original_path).name
            for candidate in candidates:
                if candidate.is_file() and candidate.name == original_name:
                    return candidate

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def _extract_job_id(self, response: requests.Response) -> Optional[str]:
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return None
        try:
            payload = response.json()
        except ValueError:
            if self.verbose:
                self._log("response JSON decode failed when extracting job id")
            return None
        if isinstance(payload, dict):
            job_id = payload.get("job_id") or payload.get("jobId")
            if isinstance(job_id, str) and job_id.strip():
                return job_id.strip()
            if self.verbose:
                self._log("response JSON did not include job_id")
        return None

    def _wait_for_job(
        self,
        job_id: str,
        *,
        timeout: int = 900,
        interval: float = 2.0,
        task: Optional[str] = None,
    ) -> None:
        status_url = self._build_url(f"/rq/api/jobstatus/{job_id}")
        end_time = time.time() + timeout
        last_status: Optional[str] = None

        while True:
            try:
                response = self.session.get(status_url, params={"_": int(time.time() * 1000)}, timeout=60)
            except requests.RequestException as exc:
                if self.verbose:
                    self._log(f"job {job_id} status request failed: {exc}")
                time.sleep(interval)
                if time.time() >= end_time:
                    raise RuntimeError(f"Timeout waiting for job {job_id}") from exc
                continue

            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                status = str(payload.get("status") or "").lower()
                if self.verbose and status and status != last_status:
                    msg = f"job {job_id} status {status}"
                    if task:
                        msg += f" ({task})"
                    self._log(msg)
                last_status = status or last_status
                if status in {"finished"}:
                    return
                if status in {"failed", "stopped", "canceled"}:
                    raise RuntimeError(f"Job {job_id} ended with status {status}")
            elif response.status_code == 404:
                if self.verbose:
                    self._log(f"job {job_id} status endpoint returned 404; assuming complete")
                return
            else:
                if self.verbose:
                    self._log(f"job {job_id} status HTTP {response.status_code}")

            if time.time() >= end_time:
                raise RuntimeError(f"Timeout waiting for job {job_id}")

            time.sleep(interval)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay recorder events against WEPPcloud.")
    parser.add_argument("profile", type=Path, help="Path to promoted profile root.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="WEPPcloud base URL.")
    parser.add_argument("--run-dir", type=Path, help="Optional run directory to use instead of cloning the profile snapshot.")
    parser.add_argument("--execute", action="store_true", help="Execute HTTP requests (default is dry-run).")
    parser.add_argument("--cookie", help="Raw Cookie header to send with each request (for authenticated playback).")
    parser.add_argument("--cookie-file", type=Path, help="Read Cookie header from file (overrides --cookie).")
    parser.add_argument("--verbose", action="store_true", help="Print progress information while replaying.")

    args = parser.parse_args(argv)

    cookie_value: Optional[str] = args.cookie
    if args.cookie_file:
        cookie_value = args.cookie_file.read_text(encoding="utf-8").strip()

    session = requests.Session()
    if cookie_value:
        session.headers.update({"Cookie": cookie_value})

    session = PlaybackSession(
        profile_root=args.profile,
        base_url=args.base_url,
        execute=args.execute,
        run_dir=args.run_dir,
        session=session,
        verbose=args.verbose,
    )
    session.run()
    print(session.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


_WAIT_SUFFIXES: Tuple[str, ...] = (
    "/query/delineation_pass/",
    "/resources/subcatchments.json",
    "/report/subcatchments/",
    "/report/channel",
)
