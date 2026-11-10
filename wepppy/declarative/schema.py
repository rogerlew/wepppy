"""Strict, dependency-free admission for the operator-only DEM slice."""

from __future__ import annotations

import json
import math
import re
from uuid import UUID

SCHEMA = "dem-v1"
PROTOCOL = "dem-engine-v1"
CONFIG = "disturbed9002"
IMAGE = re.compile(r"ghcr\.io/rogerlew/wepppy@sha256:[0-9a-f]{64}\Z")


class AdmissionError(ValueError):
    """A definition or execution observation does not meet the closed contract."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise AdmissionError("Duplicate JSON key")
        result[key] = value
    return result


def loads(value: str):
    def reject_constant(_):
        raise AdmissionError("Nonfinite JSON number")
    return json.loads(value, object_pairs_hook=_pairs, parse_constant=reject_constant)


def uuid_text(value):
    if not isinstance(value, str):
        raise AdmissionError("Identity must be a canonical UUID")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise AdmissionError("Identity must be a canonical UUID") from exc
    if str(parsed) != value:
        raise AdmissionError("Identity must be a canonical UUID")
    return value


def validate_definition(definition):
    fields = {"schema", "image", "submission_id", "extent", "source", "product", "visibility"}
    if not isinstance(definition, dict) or set(definition) != fields:
        raise AdmissionError("Definition fields do not match dem-v1")
    uuid_text(definition["submission_id"])
    for key, expected in (("schema", SCHEMA), ("source", "ned1/2024"),
                          ("product", "dem"), ("visibility", "public")):
        if definition[key] != expected:
            raise AdmissionError(f"Unsupported {key}")
    image = definition["image"]
    if not isinstance(image, str) or not IMAGE.fullmatch(image):
        raise AdmissionError("An exact approved platform image is required")
    extent = definition["extent"]
    if not isinstance(extent, list) or len(extent) != 4 or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in extent
    ):
        raise AdmissionError("Extent requires four finite numbers")
    west, south, east, north = extent
    if not (-125 <= west < east <= -66 and 24 <= south < north <= 50
            and east - west <= 0.02 and north - south <= 0.02):
        raise AdmissionError("Extent is outside the bounded CONUS slice")
    return definition


def validate(definition, approvals):
    validate_definition(definition)
    expected = {"schema": SCHEMA, "protocol": PROTOCOL, "platform": "linux/amd64",
                "operation": "fetch_dem_rq"}
    if not isinstance(approvals, dict) or approvals.get(definition["image"]) != expected:
        raise AdmissionError("Image is not approved for this protocol")
    return definition


def identities(submission_id):
    token = UUID(uuid_text(submission_id)).hex
    return f"declarative-{token}", f"declarative-dem-{token}"


def verify_evidence(definition, evidence, previous=None):
    required = {"namespace", "pod_name", "pod_uid", "container", "container_id",
                "image", "image_id", "restart_count", "platform", "node_name", "observed_at"}
    if not isinstance(evidence, dict) or set(evidence) != required:
        raise AdmissionError("Runtime evidence is incomplete")
    if any(not isinstance(evidence[k], str) or not evidence[k] for k in required - {"restart_count"}):
        raise AdmissionError("Runtime identity is incomplete")
    if (evidence["image"] != definition["image"] or evidence["image_id"] != definition["image"]
            or evidence["platform"] != "linux/amd64"
            or type(evidence["restart_count"]) is not int or evidence["restart_count"] != 0):
        raise AdmissionError("Runtime image/platform does not match the admitted manifest")
    if previous is not None and any(evidence[k] != previous[k] for k in required - {"observed_at"}):
        raise AdmissionError("Runtime was replaced or changed during execution")
    return evidence
