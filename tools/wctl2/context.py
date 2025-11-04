from __future__ import annotations

import atexit
import logging
import os
import re
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, Tuple

LOG_NAME = "wctl2"
DEFAULT_COMPOSE_RELATIVE = "docker/docker-compose.dev.yml"
_COMPOSE_ENV_PATTERN = re.compile(r"\${([A-Za-z0-9_]+)")


def _ensure_logger(level: str) -> logging.Logger:
    logger = logging.getLogger(LOG_NAME)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    try:
        numeric_level = logging._nameToLevel[level.upper()]  # type: ignore[attr-defined]
    except KeyError:
        numeric_level = logging.INFO
        logger.warning("Unknown log level '%s'; defaulting to INFO.", level)
    logger.setLevel(numeric_level)
    return logger


def _parse_env_file(path: Path) -> Iterable[Tuple[str, str]]:
    if not path.exists():
        return []
    contents = path.read_text().splitlines()
    for raw in contents:
        if not raw or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        yield key.strip(), value


def _compose_keys(path: Path) -> Sequence[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text()
    except OSError:
        return []
    return [match.group(1) for match in _COMPOSE_ENV_PATTERN.finditer(text)]


def _merge_env(
    docker_env: Path,
    host_env: Optional[Path],
    compose_path: Path,
    environ: Mapping[str, str],
) -> Tuple[OrderedDict[str, str], Dict[str, str]]:
    merged: "OrderedDict[str, str]" = OrderedDict()
    raw: Dict[str, str] = {}

    def _update_from_file(path: Path) -> None:
        for key, value in _parse_env_file(path):
            raw[key] = value
            merged[key] = value.replace("$", "$$")

    _update_from_file(docker_env)
    if host_env and host_env.exists():
        _update_from_file(host_env)

    for key in _compose_keys(compose_path):
        value = environ.get(key)
        if value is None:
            continue
        raw[key] = value
        merged[key] = value.replace("$", "$$")

    return merged, raw


def _write_temp_env(merged: Mapping[str, str]) -> Path:
    handle = tempfile.NamedTemporaryFile(prefix="wctl2-env-", suffix=".env", delete=False)
    try:
        lines = [f"{key}={value}" for key, value in merged.items()]
        handle.write("\n".join(lines).encode("utf-8"))
        if lines:
            handle.write(b"\n")
        return Path(handle.name)
    finally:
        handle.close()


def _resolve_project_dir(project_dir: Optional[str]) -> Path:
    if project_dir:
        return Path(project_dir).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _resolve_host_env(project_dir: Path, environ: Mapping[str, str]) -> Optional[Path]:
    host_override = environ.get("WCTL_HOST_ENV")
    if host_override:
        candidate = Path(host_override)
        if not candidate.is_absolute():
            candidate = project_dir / candidate
        return candidate
    default = project_dir / ".env"
    if default.exists():
        return default
    return None


@dataclass
class CLIContext:
    """
    Runtime context shared by all wctl2 commands.

    The context is responsible for locating the project directory, resolving the
    Compose file, generating a sanitised environment file, and exposing helper
    methods for command modules.
    """

    project_dir: Path
    compose_file: Path
    compose_file_relative: str
    docker_env_file: Path
    host_env_file: Optional[Path]
    env_file: Path
    env_mapping: Dict[str, str] = field(default_factory=dict)
    raw_env_mapping: Dict[str, str] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(LOG_NAME))

    @classmethod
    def from_environ(
        cls,
        *,
        project_dir: Optional[str] = None,
        compose_file: Optional[str] = None,
        environ: Optional[Mapping[str, str]] = None,
        log_level: str = "INFO",
    ) -> "CLIContext":
        env = dict(os.environ if environ is None else environ)
        logger = _ensure_logger(log_level)

        resolved_project = _resolve_project_dir(project_dir)
        docker_env = resolved_project / "docker" / ".env"
        if not docker_env.exists():
            raise FileNotFoundError(f"Expected docker/.env at {docker_env}")

        host_env = _resolve_host_env(resolved_project, env)

        compose_relative = compose_file or env.get("WCTL_COMPOSE_FILE") or DEFAULT_COMPOSE_RELATIVE
        compose_path = (resolved_project / compose_relative).resolve()
        if not compose_path.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_path}")

        merged, raw = _merge_env(docker_env, host_env, compose_path, env)
        env_file_path = _write_temp_env(merged)

        base_env = dict(env)
        base_env["WEPPPY_ENV_FILE"] = str(env_file_path)

        context = cls(
            project_dir=resolved_project,
            compose_file=compose_path,
            compose_file_relative=str(compose_relative),
            docker_env_file=docker_env,
            host_env_file=host_env,
            env_file=env_file_path,
            env_mapping=dict(base_env),
            raw_env_mapping=raw,
            logger=logger,
        )
        atexit.register(context.cleanup)
        return context

    def cleanup(self) -> None:
        if self.env_file.exists():
            try:
                self.env_file.unlink()
            except OSError:
                pass

    @property
    def environment(self) -> Dict[str, str]:
        return dict(self.env_mapping)

    def compose_base_args(self) -> Sequence[str]:
        return ("--env-file", str(self.env_file), "-f", str(self.compose_file))

    def env_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.raw_env_mapping.get(key, default)

    def is_prod(self) -> bool:
        return self.compose_file_relative.endswith("docker-compose.prod.yml")
