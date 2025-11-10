from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Optional

_TRUTHY = {"1", "true", "yes", "on"}


def _coerce_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY


def _resolve_path(path_value: Optional[str]) -> Optional[Path]:
    if not path_value:
        return None
    candidate = Path(path_value).expanduser()
    return candidate if candidate.exists() else None


DEFAULT_DATA_ROOT = Path(
    os.getenv("PROFILE_COVERAGE_DIR", "/workdir/wepppy-test-engine-data/coverage")
)
DEFAULT_CONTEXT_PREFIX = os.getenv("PROFILE_COVERAGE_CONTEXT_PREFIX", "profile")
_MODULE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path(
    os.getenv(
        "PROFILE_COVERAGE_CONFIG",
        str(_MODULE_ROOT / "weppcloud" / "coverage.profile-playback.ini"),
    )
)


@dataclass(frozen=True)
class ProfileCoverageSettings:
    enabled: bool
    data_root: Path
    context_prefix: str
    config_path: Optional[Path]

    def ensure_data_root(self, logger: Optional[logging.Logger] = None) -> bool:
        if not self.enabled:
            return False
        try:
            self.data_root.mkdir(parents=True, exist_ok=True)
            if logger:
                logger.info(
                    "Profile coverage enabled; output directory: %s", self.data_root
                )
            return True
        except OSError as exc:
            if logger:
                logger.error(
                    "Profile coverage disabled: unable to create %s (%s)",
                    self.data_root,
                    exc,
                )
            return False

    def coverage_kwargs(self, slug: str, token: str) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "data_file": str(self.data_root / f"{slug}.coverage"),
            "data_suffix": True,
            "context": f"{self.context_prefix}:{slug}:{token}",
        }
        if self.config_path:
            kwargs["config_file"] = str(self.config_path)
        return kwargs

    def log_config_status(self, logger: logging.Logger) -> None:
        if not self.enabled:
            logger.info("Profile coverage disabled via configuration or env flag.")
            return
        if self.config_path:
            logger.info("Profile coverage using config file %s", self.config_path)
        else:
            logger.warning(
                "Profile coverage config file not found; using coverage defaults."
            )


def load_settings_from_app(app) -> ProfileCoverageSettings:
    config = app.config
    enabled = bool(config.get("PROFILE_COVERAGE_ENABLED", False))
    data_root = Path(
        config.get(
            "PROFILE_COVERAGE_DIR",
            "/workdir/wepppy-test-engine-data/coverage",
        )
    )
    context_prefix = config.get("PROFILE_COVERAGE_CONTEXT_PREFIX", "profile")
    config_path = _resolve_path(config.get("PROFILE_COVERAGE_CONFIG"))
    return ProfileCoverageSettings(enabled, data_root, context_prefix, config_path)


def load_settings_from_env() -> ProfileCoverageSettings:
    enabled = _coerce_bool(os.getenv("ENABLE_PROFILE_COVERAGE"), False)
    data_root = Path(os.getenv("PROFILE_COVERAGE_DIR", DEFAULT_DATA_ROOT))
    context_prefix = os.getenv(
        "PROFILE_COVERAGE_CONTEXT_PREFIX", DEFAULT_CONTEXT_PREFIX
    )
    config_path = _resolve_path(os.getenv("PROFILE_COVERAGE_CONFIG")) or (
        DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None
    )
    return ProfileCoverageSettings(enabled, data_root, context_prefix, config_path)
