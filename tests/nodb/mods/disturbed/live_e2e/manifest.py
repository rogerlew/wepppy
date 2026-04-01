from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class LiveE2EManifest:
    raw: Dict[str, Any]

    @property
    def base_url(self) -> str:
        return str(self.raw["service"]["base_url"]).rstrip("/")

    @property
    def session_origin(self) -> str:
        return str(self.raw["service"]["session_origin"]).strip()

    @property
    def source_runid(self) -> str:
        return str(self.raw["source_run"]["runid"])

    @property
    def source_config(self) -> str:
        return str(self.raw["source_run"]["config"])

    @property
    def target_luse(self) -> str:
        return str(self.raw["target_row"]["luse"])

    @property
    def target_stext(self) -> str:
        return str(self.raw["target_row"]["stext"])

    @property
    def target_pmet_description(self) -> str:
        return str(self.raw["target_row"]["pmet_description"])

    @property
    def base_patch(self) -> Dict[str, str]:
        return {str(k): str(v) for k, v in dict(self.raw["patches"]["base"]).items()}

    @property
    def extended_patch(self) -> Dict[str, str]:
        return {str(k): str(v) for k, v in dict(self.raw["patches"]["extended"]).items()}

    @property
    def stale_sha256(self) -> str:
        return str(self.raw["negative_cases"]["stale_sha256"])

    @property
    def request_timeout_seconds(self) -> int:
        return int(self.raw["timeouts"]["request_seconds"])

    @property
    def fork_timeout_seconds(self) -> int:
        return int(self.raw["timeouts"]["fork_seconds"])

    @property
    def build_soils_timeout_seconds(self) -> int:
        return int(self.raw["timeouts"]["build_soils_seconds"])

    @property
    def prep_wepp_timeout_seconds(self) -> int:
        return int(self.raw["timeouts"]["prep_wepp_seconds"])

    @property
    def poll_interval_seconds(self) -> int:
        return int(self.raw["timeouts"]["poll_interval_seconds"])

    @property
    def target_sol_fields(self) -> list[str]:
        return [str(item) for item in self.raw["artifacts"]["target_sol_fields"]]

    @property
    def target_management_fields(self) -> list[str]:
        return [str(item) for item in self.raw["artifacts"]["target_management_fields"]]

    @property
    def dev_agent_credentials_file(self) -> str:
        return str(self.raw["inputs"]["dev_agent_credentials_file"])


def _manifest_path(path: str | Path | None = None) -> Path:
    if path is None:
        return Path(__file__).with_name("manifest.json")
    return Path(path)


def load_manifest(path: str | Path | None = None) -> LiveE2EManifest:
    manifest_path = _manifest_path(path)
    raw = json.loads(manifest_path.read_text())

    env_overrides: dict[tuple[str, str], str] = {
        ("service", "base_url"): "DISTURBED_LOOKUP_LIVE_E2E_BASE_URL",
        ("service", "session_origin"): "DISTURBED_LOOKUP_LIVE_E2E_SESSION_ORIGIN",
        ("source_run", "runid"): "DISTURBED_LOOKUP_LIVE_E2E_SOURCE_RUNID",
        ("source_run", "config"): "DISTURBED_LOOKUP_LIVE_E2E_SOURCE_CONFIG",
        (
            "inputs",
            "dev_agent_credentials_file",
        ): "DISTURBED_LOOKUP_LIVE_E2E_DEV_AGENT_CREDENTIALS_FILE",
    }

    for (section, key), env_key in env_overrides.items():
        value = os.getenv(env_key)
        if value is None:
            continue
        raw.setdefault(section, {})
        raw[section][key] = value

    return LiveE2EManifest(raw=raw)
