"""Data-only catalog extraction; no controller construction or file repair."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os

from wepppy.weppcloud.utils.run_ttl import _normalize_payload
from .paths import Roots, SourceScopeError, project_directory, read_source

__all__ = ["Observation", "Snapshot", "extract", "decode_ron", "decode_ttl"]


@dataclass
class Observation:
    state: str
    values: dict = field(default_factory=dict)
    version: dict = field(default_factory=dict)
    error: str | None = None
    binding: tuple = ()


@dataclass
class Snapshot:
    locator: str | None
    sources: dict[str, Observation]
    verify: object = None


def _sequence(value):
    return value.get("py/tuple") if isinstance(value, dict) and set(value) == {"py/tuple"} else value


def decode_ron(payload):
    data = json.loads(payload)
    if isinstance(data, dict) and "py/state" in data:
        data = data["py/state"]
    if not isinstance(data, dict) or not isinstance(data.get("_name"), str):
        raise ValueError("Unsupported Ron metadata")
    scenario = data.get("_scenario", "")
    if not isinstance(scenario, str) or "\u0000" in scenario or "\u0000" in data["_name"]:
        raise ValueError("Unsupported scenario")
    values = dict(name=data["_name"], scenario=scenario, map_lng=None, map_lat=None, map_zoom=None)
    map_data = data.get("_map")
    if map_data is None:
        return values, None
    try:
        if isinstance(map_data, str):
            map_data = json.loads(map_data)
        if isinstance(map_data, dict) and "py/state" in map_data:
            map_data = map_data["py/state"]
        if not isinstance(map_data, dict):
            raise ValueError("Unsupported map")
        center = _sequence(map_data.get("center"))
        if not isinstance(center, (list, tuple)) or len(center) != 2:
            raise ValueError("Unsupported center")
        longitude, latitude = (float(value) for value in center)
        zoom = float(map_data["zoom"])
        if not all(math.isfinite(value) for value in (longitude, latitude, zoom)):
            raise ValueError("Nonfinite map")
        values.update(map_lng=longitude, map_lat=latitude, map_zoom=zoom)
    except (ValueError, TypeError, KeyError, OverflowError):
        return values, "unsupported_map"
    return values, None


def decode_ttl(payload):
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("TTL is not a mapping")
    data = _normalize_payload(data)
    policy = data.get("policy")
    policy = policy if isinstance(policy, str) else None
    expiration = None
    raw = data.get("expires_at")
    if policy == "rolling_90d" and isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                expiration = parsed.astimezone(timezone.utc)
        except (ValueError, OverflowError):
            pass
    return dict(ttl_policy=policy, ttl_deletion_at=expiration), None


def _observe(descriptor, source, locators, now):
    filename = {"ron": "ron.nodb", "readonly": "READONLY", "ttl": "TTL"}[source]
    try:
        payload, details, binding = read_source(descriptor, filename, locators)
    except FileNotFoundError:
        state = "ready" if source == "readonly" else "missing"
        return Observation(state, {"readonly": False} if source == "readonly" else {},
                           {"state": state, "absent": True, "observed_at": now.isoformat()})
    except OSError as error:
        return Observation("unreadable", error="source_scope_mismatch" if isinstance(error, SourceScopeError) else "source_io_error")
    version = dict(state="ready",
                   device=details.st_dev, inode=details.st_ino, size=details.st_size,
                   mtime_ns=details.st_mtime_ns, observed_at=now.isoformat())
    if source != "readonly":
        version["sha256"] = hashlib.sha256(payload).hexdigest()
    try:
        if source == "readonly":
            values, diagnostic = {"readonly": True}, None
        else:
            values, diagnostic = (decode_ron if source == "ron" else decode_ttl)(payload)
        return Observation("ready", values, version, diagnostic, binding)
    except (ValueError, UnicodeDecodeError, RecursionError):
        version["state"] = "invalid"
        return Observation("invalid", version=version, error="source_invalid", binding=binding)


def _binding(runid, roots):
    for root, relative in roots.candidates(runid):
        try:
            with project_directory(root, relative) as (_, chain):
                return root, relative, chain
        except FileNotFoundError:
            continue
    return None


def extract(runid, roots=None, now=None):
    roots = roots or Roots.from_environ()
    now = now or datetime.now(timezone.utc)
    snapshot = Snapshot(None, {
        "ron": Observation("missing", version={"state": "missing", "absent": True, "observed_at": now.isoformat()}),
        "readonly": Observation("ready", {"readonly": False}, {"state": "ready", "absent": True, "observed_at": now.isoformat()}),
        "ttl": Observation("missing", version={"state": "missing", "absent": True, "observed_at": now.isoformat()}),
    })
    try:
        selected = _binding(runid, roots)
        if selected is not None:
            root, relative, chain = selected
            snapshot.locator = os.path.join(os.path.realpath(root), *relative)
            locators = (snapshot.locator, os.path.join(os.path.abspath(root), *relative))
            with project_directory(root, relative) as (descriptor, opened_chain):
                if chain != opened_chain:
                    raise SourceScopeError("source_drift")
                snapshot.sources = {source: _observe(descriptor, source, locators, now)
                                    for source in ("ron", "readonly", "ttl")}

        def verify():
            try:
                if _binding(runid, roots) != selected:
                    raise SourceScopeError("source_drift")
                if selected is not None:
                    with project_directory(root, relative) as (descriptor, current_chain):
                        if current_chain != chain:
                            raise SourceScopeError("source_drift")
                        for source, observation in list(snapshot.sources.items()):
                            if observation.state == "unreadable":
                                continue
                            check = _observe(descriptor, source, locators, now)
                            if check.version != observation.version or check.binding != observation.binding:
                                snapshot.sources[source] = Observation("unreadable", error="source_drift")
            except OSError:
                snapshot.sources = {source: Observation("unreadable", error="source_drift")
                                    for source in ("ron", "readonly", "ttl")}

        snapshot.verify = verify
        verify()
    except (OSError, ValueError) as error:
        code = "source_scope_mismatch" if isinstance(error, (SourceScopeError, ValueError)) else "source_io_error"
        snapshot.sources = {source: Observation("unreadable", error=code)
                            for source in ("ron", "readonly", "ttl")}
    return snapshot
