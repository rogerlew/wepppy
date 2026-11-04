"""Roads-owned retained baselines and native input overrides (resolver version 1).

This module owns values and artifact transformations, not NoDb mutations or locks.
See docs/schemas/roads-settings-contract.md for the saved-state authority.
"""
from __future__ import annotations

import copy
import hashlib
from functools import lru_cache
import json
import math
import re
import shlex
import struct
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

UNBOUND = object()
ROLES = ("road", "fill", "buffer")
PARAMETERS = ("ksat_mm_h", "ki_kg_s_m4", "kr_s_m", "critical_shear_pa")
_HEADER_INDEX = {"ksat_mm_h": 8, "ki_kg_s_m4": 5, "kr_s_m": 6, "critical_shear_pa": 7}
_SOURCE_NAMES = ("Road", "Fill", "Forest")
_MARKERS = ("urr", "ufr", "ubr")
TEMPLATE_ROOT = Path(__file__).parent / "legacy_templates"
ASSET_NAMES = frozenset(
    [f"soils/3g{texture}{suffix}.sol" for texture in ("clay", "loam", "sand", "silt") for suffix in ("2", "10")]
    + [f"soils/3p{texture}{suffix}.sol" for texture in ("clay", "loam", "sand", "silt") for suffix in ("1", "10")]
    + ["managements/3inslope.man", "managements/3inslopen.man"]
)
_MAX_ASSET_BYTES = 256 * 1024
_MAX_TOTAL_BYTES = 1024 * 1024
_TOKEN = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")

__all__ = ["UNBOUND", "ROLES", "PARAMETERS", "ASSET_NAMES", "default_overrides", "bind_baseline",
           "new_state", "validate_state", "apply_payload", "configuration_hash",
           "materialize_baseline", "resolve_groups", "apply_soil_overrides",
           "soil_template_name", "management_template_name", "baseline_identity"]


def _exact_keys(value: Any, keys: set[str], context: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{context} must contain exactly {', '.join(sorted(keys))}.")


def _number(value: Any, context: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a finite number.")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{context} is outside numeric representation.") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{context} must be finite{' and positive' if positive else ''}.")
    return result


def _native_real(value: float, context: str) -> None:
    """Reject native REAL overflow/underflow before any solver sees the field."""
    try:
        native = struct.unpack("f", struct.pack("f", value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError(f"{context} exceeds native numeric representation.") from exc
    if not math.isfinite(native) or (value != 0 and native == 0):
        raise ValueError(f"{context} exceeds native numeric representation.")


def _native_value(value: Any, parameter: str, context: str, *, serialize: bool = False) -> float:
    """Validate the emitted 6-significant-digit value and native REAL conversion."""
    numeric = _number(value, context, positive=True)
    emitted = float(f"{numeric:.6g}") if serialize else numeric
    try:
        native = struct.unpack("f", struct.pack("f", emitted))[0]
        if parameter == "ksat_mm_h":
            native = struct.unpack("f", struct.pack("f", native / 3.6e6))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError(f"{context} exceeds native numeric representation.") from exc
    if not math.isfinite(native) or native <= 0:
        raise ValueError(f"{context} must remain finite and positive in native representation.")
    return emitted


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def baseline_identity(assets: Mapping[str, Mapping[str, str]]) -> str:
    manifest = {"resolver_version": 1, "assets": {key: value["sha256"] for key, value in assets.items()}}
    return "roads-legacy-v1-" + _digest(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())


def default_overrides() -> dict[str, dict[str, dict[str, Any]]]:
    return {role: {key: {"mode": "default"} for key in PARAMETERS} for role in ROLES}


def _soil_rows(text: str, name: str) -> list[dict[str, float]]:
    """Check raw legacy tokens before the owned parser can normalize them."""
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) != 9 or lines[0] != "98.4" or lines[2].split() != ["3", "0"]:
        raise ValueError(f"{name}: expected a three-role, one-horizon 98.4 baseline soil.")
    result = []
    for index, role in enumerate(ROLES):
        header = shlex.split(lines[3 + 2 * index])
        horizon = lines[4 + 2 * index].split()
        if len(header) != 9 or header[0] != _SOURCE_NAMES[index] or header[2] != "1":
            raise ValueError(f"{name}: invalid {role} source header.")
        if header[1] not in {"clay loam", "loam", "sandy loam", "silt loam"}:
            raise ValueError(f"{name}: unsupported soil texture.")
        if len(horizon) != 6 or horizon[-1] != _MARKERS[index]:
            raise ValueError(f"{name}: invalid {role} fragment marker or horizon shape.")
        try:
            numbers = [float(token) for token in header[3:]]
            layer = [float(token) for token in horizon[:5]]
        except ValueError as exc:
            raise ValueError(f"{name}: nonnumeric {role} soil field.") from exc
        if not all(math.isfinite(value) for value in numbers + layer):
            raise ValueError(f"{name}: nonfinite {role} soil field.")
        for value in numbers + layer:
            _native_real(value, f"{name} {role} raw soil field")
        if not (0 <= numbers[0] <= 1 and 0 <= numbers[1] <= 1):
            raise ValueError(f"{name}: invalid {role} albedo or saturation.")
        depth, sand, clay, organic, cec = layer
        if depth <= 0 or not (0 <= sand <= 100 and 0 <= clay <= 100 and sand + clay <= 100):
            raise ValueError(f"{name}: invalid {role} horizon depth or texture.")
        if not (0 <= organic <= 100 and cec >= 0):
            raise ValueError(f"{name}: invalid {role} organic matter or CEC.")
        result.append({key: _native_value(float(header[column]), key, f"{name} {role} {key}")
                       for key, column in _HEADER_INDEX.items()})
    return result


def _validate_management_numbers(text: str, name: str) -> None:
    lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if len(lines) < 3 or lines[:2] != ["97.3", "3"]:
        raise ValueError(f"{name}: expected a three-OFE 97.3 management template.")
    # Reject nonfinite numeric tokens before permissive legacy parsing. Native names
    # and human-readable description lines remain strings, not paths to execute.
    for line in lines:
        for token in line.split():
            try:
                numeric = float(token)
            except ValueError:
                continue
            if not math.isfinite(numeric):
                raise ValueError(f"{name}: nonfinite management field.")
            _native_real(numeric, f"{name} raw management field")


@lru_cache(maxsize=36)
def _validate_parsed_asset(name: str, text: str) -> None:
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.management.managements import Management

    # Cache only validation of exact immutable text; identity/hash/shape checks
    # still run for every state. No cached model value is authoritative.
    with tempfile.TemporaryDirectory(prefix="roads-baseline-validation-") as scratch:
        path = Path(scratch) / Path(name).name
        if name.startswith("managements/"):
            # The owned parser recognizes #landuse to preserve the preceding
            # blank description lines. Legacy Roads spells this comment with
            # backticks. Normalize comments in validation scratch only: retained
            # text and emitted native bytes are never rewritten by this adapter.
            text = text.replace("# `landuse'", "#landuse")
        path.write_bytes(text.encode("utf-8"))
        try:
            if name.startswith("soils/"):
                parsed = WeppSoilUtil(str(path), compute_erodibilities=False, compute_conductivity=False)
                if len(parsed.obj["ofes"]) != 3:
                    raise ValueError("Expected three soil roles.")
            else:
                parsed_man = Management(Key=None, ManagementFile=path.name,
                                        ManagementDir=str(path.parent), Color=(0, 0, 0, 0),
                                        StrictLegacyRoads=True, InputMaxOfes=3)
                if parsed_man.datver != "97.3" or parsed_man.nofe != 3:
                    raise ValueError("Expected three management OFEs.")
        except (ValueError, IndexError, KeyError, TypeError, AssertionError, OverflowError) as exc:
            raise ValueError(f"Invalid retained Roads baseline asset {name}: {exc}") from exc


def _validate_baseline(baseline: Any) -> None:
    _exact_keys(baseline, {"id", "resolver_version", "assets"}, "baseline")
    if type(baseline["resolver_version"]) is not int or baseline["resolver_version"] != 1:
        raise ValueError("Unsupported Roads parameterization resolver version.")
    assets = baseline["assets"]
    if not isinstance(assets, dict) or set(assets) != ASSET_NAMES:
        raise ValueError("Baseline must contain the exact 18 allowed Roads assets.")
    total = 0
    for name in sorted(ASSET_NAMES):
        asset = assets[name]
        _exact_keys(asset, {"text", "sha256"}, f"asset {name}")
        if not isinstance(asset["text"], str) or "\x00" in asset["text"]:
            raise ValueError(f"{name}: expected plain UTF-8 text without NUL.")
        try:
            encoded = asset["text"].encode("utf-8")
        except UnicodeError as exc:
            raise ValueError(f"{name}: invalid UTF-8 text.") from exc
        total += len(encoded)
        if len(encoded) > _MAX_ASSET_BYTES or total > _MAX_TOTAL_BYTES:
            raise ValueError("Retained Roads baseline exceeds allowed size.")
        if asset["sha256"] != _digest(encoded):
            raise ValueError(f"{name}: baseline asset hash mismatch.")
        if name.startswith("soils/"):
            _soil_rows(asset["text"], name)
        else:
            _validate_management_numbers(asset["text"], name)
    if baseline["id"] != baseline_identity(assets):
        raise ValueError("Roads baseline identity mismatch.")
    for name, asset in assets.items():
        _validate_parsed_asset(name, asset["text"])


def bind_baseline(template_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(template_root) if template_root is not None else TEMPLATE_ROOT
    assets = {}
    for name in sorted(ASSET_NAMES):
        path = root / name
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError(f"Refusing symlinked baseline asset {name}.")
        raw = path.read_bytes()
        assets[name] = {"text": raw.decode("utf-8"), "sha256": _digest(raw)}
    baseline = {"id": baseline_identity(assets), "resolver_version": 1, "assets": assets}
    _validate_baseline(baseline)
    return baseline


def _validate_overrides(overrides: Any) -> None:
    _exact_keys(overrides, set(ROLES), "overrides")
    for role in ROLES:
        _exact_keys(overrides[role], set(PARAMETERS), f"{role} overrides")
        for key in PARAMETERS:
            entry = overrides[role][key]
            if not isinstance(entry, dict) or entry.get("mode") not in ("default", "multiply", "absolute"):
                raise ValueError(f"{role} {key}: unsupported override mode.")
            keys = {"mode"} if entry["mode"] == "default" else {"mode", "value"}
            _exact_keys(entry, keys, f"{role} {key} override")
            if entry["mode"] != "default":
                _native_value(entry["value"], key if entry["mode"] == "absolute" else "factor",
                              f"{role} {key} requested override")


def _resolved_value(baseline: float, entry: Mapping[str, Any], parameter: str, context: str) -> float:
    if entry["mode"] == "default":
        value = baseline
    elif entry["mode"] == "multiply":
        value = baseline * entry["value"]
    else:
        value = entry["value"]
    return _native_value(value, parameter, context, serialize=entry["mode"] != "default")


def _resolved_groups(state: Mapping[str, Any], soil_name: str, traffic: str) -> list[dict[str, Any]]:
    if traffic not in ("high", "low", "none"):
        raise ValueError("Unsupported Roads traffic value.")
    name = soil_name if soil_name.startswith("soils/") else f"soils/{soil_name}"
    if name not in ASSET_NAMES or not name.startswith("soils/"):
        raise ValueError("Unsupported Roads soil template.")
    rows = _soil_rows(state["baseline"]["assets"][name]["text"], name)
    result = []
    for role, baseline in zip(ROLES, rows):
        adjusted = dict(baseline)
        if role == "road":
            divisor = 1 if traffic == "high" else 4
            for key in ("ki_kg_s_m4", "kr_s_m"):
                adjusted[key] = _native_value(adjusted[key] / divisor, key, f"{role} adjusted {key}", serialize=True)
        entries = state["overrides"][role]
        resolved = {key: _resolved_value(adjusted[key], entries[key], key, f"{role} resolved {key}") for key in PARAMETERS}
        result.append({"role": role, "baseline": baseline, "adjusted": adjusted,
                       "overrides": copy.deepcopy(entries), "resolved": resolved,
                       "source_asset": name, "source_sha256": state["baseline"]["assets"][name]["sha256"]})
    return result


def validate_state(state: Any) -> dict[str, Any]:
    _exact_keys(state, {"schema_version", "baseline", "overrides"}, "parameterization")
    if type(state["schema_version"]) is not int or state["schema_version"] != 1:
        raise ValueError("Unsupported Roads parameterization schema version.")
    _validate_baseline(state["baseline"])
    _validate_overrides(state["overrides"])
    for name in sorted(ASSET_NAMES):
        if name.startswith("soils/"):
            for traffic in ("high", "low", "none"):
                _resolved_groups(state, name, traffic)
    return copy.deepcopy(state)


def new_state(template_root: str | Path | None = None, overrides: Any = None) -> dict[str, Any]:
    state = {"schema_version": 1, "baseline": bind_baseline(template_root),
             "overrides": default_overrides() if overrides is None else copy.deepcopy(overrides)}
    return validate_state(state)


def apply_payload(current_state: Any, payload: Any, template_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict) or not set(payload).issubset({"overrides", "repair"}) or "overrides" not in payload:
        raise ValueError("parameterization accepts overrides and optional repair:true only.")
    if "repair" in payload and payload["repair"] is not True:
        raise ValueError("repair must be JSON boolean true when supplied.")
    repair = payload.get("repair", False)
    _validate_overrides(payload["overrides"])
    if repair:
        if payload["overrides"] != default_overrides():
            raise ValueError("Repair requires all overrides in default mode.")
        if current_state is UNBOUND:
            raise ValueError("Unbound parameterization does not require repair.")
        try:
            validate_state(current_state)
        except ValueError:
            return new_state(template_root)
        raise ValueError("Valid bound parameterization cannot be repaired or rebased.")
    if current_state is UNBOUND:
        return new_state(template_root, payload["overrides"])
    state = validate_state(current_state)
    state["overrides"] = copy.deepcopy(payload["overrides"])
    return validate_state(state)


def configuration_hash(state: Any) -> str:
    # Callers obtain this only after validated hydration/mutation; no parser I/O.
    return _digest(json.dumps(state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def materialize_baseline(state: Any, parent_dir: str | Path) -> Path:
    validated = validate_state(state)
    parent = Path(parent_dir)
    if not parent.is_dir() or any(part.is_symlink() for part in (parent, *parent.parents)):
        raise ValueError("Retained templates require an existing nonsymlink Roads scratch parent.")
    target = Path(tempfile.mkdtemp(prefix="parameterization-", dir=parent))
    for name, asset in validated["baseline"]["assets"].items():
        path = target / name
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            stream.write(asset["text"].encode("utf-8"))
    return target


def soil_template_name(design: str, surface: str, soil_texture: str) -> str:
    if surface not in ("gravel", "paved") or soil_texture not in ("clay", "loam", "sand", "silt"):
        raise ValueError("Unsupported Roads surface or soil texture.")
    if design not in ("inslope_rd", "inslope_bd", "outslope_rutted", "outslope_unrutted"):
        raise ValueError("Unsupported Roads design.")
    suffix = "10" if design == "inslope_rd" else ("1" if surface == "paved" else "2")
    return f"3{'p' if surface == 'paved' else 'g'}{soil_texture}{suffix}.sol"


def management_template_name(traffic: str) -> str:
    if traffic not in ("high", "low", "none"):
        raise ValueError("Unsupported Roads traffic value.")
    return "3inslopen.man" if traffic == "none" else "3inslope.man"


def resolve_groups(state: Any, soil_name: str, traffic: str) -> list[dict[str, Any]]:
    return _resolved_groups(validate_state(state), soil_name, traffic)


def _emitted_headers(path: Path) -> tuple[list[str], list[tuple[int, list[str]]]]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    active = [(index, line.strip()) for index, line in enumerate(lines) if line.strip() and not line.lstrip().startswith("#")]
    if len(active) < 3 or active[0][1] != "98.4":
        raise ValueError("Roads overrides require assembled legacy 98.4 soil.")
    count = int(active[2][1].split()[0])
    cursor, headers = 3, []
    for _ in range(count):
        if cursor >= len(active):
            raise ValueError("Incomplete assembled soil header.")
        index, text = active[cursor]
        tokens = shlex.split(text)
        if len(tokens) != 9:
            raise ValueError("Malformed assembled soil header.")
        layers = int(tokens[2])
        if layers < 1 or cursor + layers >= len(active):
            raise ValueError("Incomplete assembled soil horizons.")
        headers.append((index, tokens))
        cursor += 1 + layers
    if cursor != len(active):
        raise ValueError("Unexpected trailing assembled soil records.")
    return lines, headers


def apply_soil_overrides(path: str | Path, state: Any, ofe_order: Sequence[int], *,
                         template_name: str, traffic: str) -> dict[str, Any]:
    validated = validate_state(state)
    soil = Path(path)
    if soil.is_symlink():
        raise ValueError("Refusing to override symlinked soil input.")
    groups = _resolved_groups(validated, template_name, traffic)
    lines, headers = _emitted_headers(soil)
    if len(headers) != len(ofe_order) or any(type(role) is not int or role not in (1, 2, 3) for role in ofe_order):
        raise ValueError("Soil role order does not match emitted inputs.")
    records, changed = [], False
    for position, ((line_index, tokens), role_index) in enumerate(zip(headers, ofe_order), 1):
        group = groups[role_index - 1]
        if tokens[0] != _SOURCE_NAMES[role_index - 1]:
            raise ValueError("Assembled soil role does not match source role order.")
        emitted = {}
        replacements = {}
        for key, column in _HEADER_INDEX.items():
            current = _native_value(float(tokens[column]), key, f"OFE {position} {key}")
            if current != group["adjusted"][key]:
                raise ValueError(f"OFE {position} {key} does not match its bound baseline adjustment.")
            target = group["resolved"][key]
            if group["overrides"][key]["mode"] != "default":
                replacements[column] = f"{target:.6g}"
            emitted[key] = target
        if replacements:
            spans = list(_TOKEN.finditer(lines[line_index]))
            text = lines[line_index]
            for column in sorted(replacements, reverse=True):
                match = spans[column]
                text = text[:match.start()] + replacements[column] + text[match.end():]
            lines[line_index] = text
            changed = True
        records.append({"ofe_index": position, "role": group["role"], "baseline": group["baseline"],
                        "adjusted": group["adjusted"], "requested": group["overrides"],
                        "resolved": group["resolved"], "emitted": emitted})
    if changed:
        soil.write_text("".join(lines), encoding="utf-8")
    _, readback = _emitted_headers(soil)
    for record, (_, tokens) in zip(records, readback):
        actual = {key: float(tokens[column]) for key, column in _HEADER_INDEX.items()}
        if actual != record["emitted"]:
            raise ValueError("Roads override readback differs from resolved values.")
        record["emitted"] = actual
    source_name = template_name if template_name.startswith("soils/") else f"soils/{template_name}"
    man_name = "managements/" + management_template_name(traffic)
    return {"baseline_id": validated["baseline"]["id"], "configuration_hash": configuration_hash(validated),
            "source_asset_hashes": {name: validated["baseline"]["assets"][name]["sha256"] for name in (source_name, man_name)},
            "ofes": records, "input_files": [{"relpath": soil.name, "sha256": _digest(soil.read_bytes())}]}
