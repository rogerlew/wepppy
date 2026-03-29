"""Built-in and text-loaded profile helpers for features export."""

from __future__ import annotations

import collections.abc as cabc
import json
from pathlib import Path
import re

import yaml

_PROFILE_KEY_PATTERN = re.compile(r"[^a-z0-9_]+")
_PREFERRED_PROFILE_ORDER: tuple[str, ...] = ("prep_details", "post_wepp")


class FeaturesExportProfileError(ValueError):
    """Raised when a profile document is malformed."""


def default_profiles_dir() -> Path:
    """Return built-in profile directory path."""

    return Path(__file__).resolve().parent / "profiles"


def normalize_profile_key(value: str) -> str:
    """Normalize one profile key token to snake_case."""

    token = str(value or "").strip().lower().replace("-", "_")
    token = _PROFILE_KEY_PATTERN.sub("_", token).strip("_")
    return token


def parse_profile_text(profile_text: str) -> dict[str, object]:
    """Parse one profile text payload and return a request mapping."""

    if not isinstance(profile_text, str) or not profile_text.strip():
        raise FeaturesExportProfileError("Profile text must be a non-empty string.")

    try:
        parsed = yaml.safe_load(profile_text)
    except yaml.YAMLError as exc:
        raise FeaturesExportProfileError(f"Profile text is not valid YAML: {exc}") from exc

    return _extract_request_mapping(parsed, source="<profile_text>")


def load_builtin_profiles(
    *,
    profiles_dir: str | Path | None = None,
) -> tuple[dict[str, object], ...]:
    """Load built-in `.yml` profiles from disk in stable order."""

    root = Path(profiles_dir).resolve() if profiles_dir is not None else default_profiles_dir()
    if not root.is_dir():
        return ()

    loaded: list[dict[str, object]] = []
    for path in sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise FeaturesExportProfileError(
                f"Profile file {path.name!r} is not valid YAML: {exc}"
            ) from exc

        request_mapping = _extract_request_mapping(parsed, source=path.name)
        key = _profile_key_from_document(parsed, path=path)
        label = _profile_label_from_document(parsed, fallback=path.stem)
        description = _profile_description_from_document(parsed)
        loaded.append(
            {
                "key": key,
                "label": label,
                "description": description,
                "request": request_mapping,
                "relpath": f"profiles/{path.name}",
                "path": str(path),
            }
        )

    return tuple(
        sorted(
            loaded,
            key=lambda item: (_profile_order_index(str(item.get("key") or "")), str(item.get("key") or "")),
        )
    )


def profile_bundle_member_sources(
    *,
    profiles_dir: str | Path | None = None,
) -> dict[str, Path]:
    """Return mapping of zip relpath -> source file for built-in profiles."""

    members: dict[str, Path] = {}
    for profile in load_builtin_profiles(profiles_dir=profiles_dir):
        relpath = str(profile.get("relpath") or "").strip()
        source = str(profile.get("path") or "").strip()
        if not relpath or not source:
            continue
        members[relpath] = Path(source).resolve()
    return members


def _profile_order_index(key: str) -> int:
    try:
        return _PREFERRED_PROFILE_ORDER.index(key)
    except ValueError:
        return len(_PREFERRED_PROFILE_ORDER)


def _extract_request_mapping(value: object, *, source: str) -> dict[str, object]:
    if not isinstance(value, cabc.Mapping):
        raise FeaturesExportProfileError(
            f"Profile document {source!r} must decode to an object mapping."
        )

    request_candidate = value.get("request", value)
    if not isinstance(request_candidate, cabc.Mapping):
        raise FeaturesExportProfileError(
            f"Profile document {source!r} must include a mapping under 'request'."
        )

    normalized = _normalize_mapping(request_candidate)
    if not normalized:
        raise FeaturesExportProfileError(
            f"Profile document {source!r} resolved to an empty request mapping."
        )
    return normalized


def _profile_key_from_document(value: object, *, path: Path) -> str:
    if isinstance(value, cabc.Mapping):
        raw = value.get("profile_id", path.stem)
    else:
        raw = path.stem
    key = normalize_profile_key(str(raw or ""))
    if not key:
        key = normalize_profile_key(path.stem)
    if not key:
        raise FeaturesExportProfileError(f"Unable to derive profile key from {path.name!r}.")
    return key


def _profile_label_from_document(value: object, *, fallback: str) -> str:
    if isinstance(value, cabc.Mapping):
        raw = value.get("label")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    words = [token.capitalize() for token in normalize_profile_key(fallback).split("_") if token]
    return " ".join(words) if words else fallback


def _profile_description_from_document(value: object) -> str:
    if isinstance(value, cabc.Mapping):
        raw = value.get("description")
        if isinstance(raw, str):
            return raw.strip()
    return ""


def _normalize_mapping(value: cabc.Mapping[str, object]) -> dict[str, object]:
    normalized = {str(key): item for key, item in value.items()}
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    parsed = json.loads(serialized)
    if not isinstance(parsed, dict):
        raise FeaturesExportProfileError("Profile normalization produced a non-object payload.")
    return parsed


__all__ = [
    "FeaturesExportProfileError",
    "default_profiles_dir",
    "load_builtin_profiles",
    "normalize_profile_key",
    "parse_profile_text",
    "profile_bundle_member_sources",
]

