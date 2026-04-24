"""Routes for landuse blueprint extracted from app.py."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple
from urllib.parse import quote
from uuid import uuid4

from flask import Response

from .._common import (
    Blueprint,
    authorize,
    authorize_and_handle_with_exception_factory,
    error_factory,
    jsonify,
    load_run_context,
    make_response,
    render_template,
)
from .._common import exception_factory, get_wd

from wepppy.microservices.shape_converter.archive_validation import (
    ArchiveLimits,
    validate_and_extract_zip_archive,  # noqa: F401 - re-exported for rq_engine landuse routes
)
from wepppy.microservices.shape_converter.errors import ShapeConverterError
from wepppy.microservices.upload_boundary import (
    UploadBoundaryError,  # noqa: F401 - re-exported for rq_engine landuse routes
    save_upload_from_stream,  # noqa: F401 - re-exported for rq_engine landuse routes
)
from wepppy.nodb.core import Landuse, LanduseCustomMappingError, Ron
from wepppy.wepp.management import ManagementMapLoadError, WEPPPY_MAN_DIR, load_map, read_management
from wepppy.weppcloud.utils.cap_guard import requires_cap


landuse_bp = Blueprint('landuse', __name__)

_DISTURBED_PREVIEW_TEXTURES: tuple[tuple[str, str], ...] = (
    ("clay", "Clay"),
    ("loam", "Loam"),
    ("sand", "Sand"),
    ("silt", "Silt"),
)

_CATALOG_SCHEMA_VERSION = 1
_LANDUSE_USER_DEFINED_RELPATH = Path("landuse") / "user-defined"
_LANDUSE_CATALOG_FILENAME = "management_catalog.json"
_LANDUSE_MAPPING_OVERRIDE_RELPATH = "landuse/landuse_user_defined_mapping.json"
_LANDUSE_ALLOWED_MAN_EXTENSIONS = ("man",)
_LANDUSE_ALLOWED_ARCHIVE_EXTENSIONS = ("zip",)
_LANDUSE_MAN_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
_LANDUSE_ZIP_UPLOAD_MAX_BYTES = 50 * 1024 * 1024
_LANDUSE_ZIP_EXTRACTED_MAX_BYTES = 250 * 1024 * 1024
_LANDUSE_ZIP_MEMBER_LIMIT = 500
_LANDUSE_MANAGEMENT_FILE_KEY_MAX_LENGTH = 512
_LANDUSE_MAP_MISSING_CODE = "LANDUSE_CUSTOM_MAP_MISSING"
_LANDUSE_MAP_INVALID_CODE = "LANDUSE_CUSTOM_MAP_INVALID"
_MACOS_ARCHIVE_METADATA_DIR = "__MACOSX"
_LANDUSE_ZIP_LIMITS = ArchiveLimits(
    max_compressed_bytes=_LANDUSE_ZIP_UPLOAD_MAX_BYTES,
    max_uncompressed_bytes=_LANDUSE_ZIP_EXTRACTED_MAX_BYTES,
    max_member_count=_LANDUSE_ZIP_MEMBER_LIMIT,
)


def _set_no_store_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _utc_iso_timestamp() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def _validate_run_scoped_path(path: Path, wd: str, *, label: str) -> Path:
    run_root = Path(wd).resolve()
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise ValueError(f"{label} is not accessible: {path}") from exc
    if resolved != run_root and run_root not in resolved.parents:
        raise ValueError(f"{label} escapes run root: {path}")
    return path


def _landuse_user_defined_dir(wd: str) -> Path:
    path = Path(wd) / _LANDUSE_USER_DEFINED_RELPATH
    return _validate_run_scoped_path(path, wd, label="landuse user-defined directory")


def _landuse_catalog_path(wd: str) -> Path:
    return _landuse_user_defined_dir(wd) / _LANDUSE_CATALOG_FILENAME


def _landuse_mapping_override_path(wd: str) -> Path:
    path = Path(wd) / _LANDUSE_MAPPING_OVERRIDE_RELPATH
    return _validate_run_scoped_path(path, wd, label="landuse mapping override path")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        with tmp_path.open("wb") as handle:
            handle.write(payload)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _safe_catalog_filename(raw_name: str) -> str:
    from werkzeug.utils import secure_filename

    safe_name = secure_filename(raw_name)
    if not safe_name:
        raise ValueError("Invalid filename")
    if not safe_name.lower().endswith(".man"):
        raise ValueError("Management upload must use .man extension")
    return safe_name.lower()


def _catalog_default_description(filename: str) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem if stem else filename


def _read_catalog_metadata(wd: str) -> dict[str, Any]:
    path = _landuse_catalog_path(wd)
    if not path.exists():
        return {"schema_version": _CATALOG_SCHEMA_VERSION, "items": []}

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Management catalog metadata must be a JSON object")
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Management catalog metadata items must be a list")

    normalized_items: list[dict[str, Any]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        filename = raw_item.get("filename")
        if filename is None:
            continue
        try:
            safe_filename = _safe_catalog_filename(str(filename))
        except ValueError:
            continue
        description = str(raw_item.get("description") or "").strip()
        if not description:
            description = _catalog_default_description(safe_filename)
        normalized_items.append(
            {
                "filename": safe_filename,
                "description": description,
                "uploaded_at": str(raw_item.get("uploaded_at") or "").strip() or _utc_iso_timestamp(),
            }
        )

    normalized_items.sort(key=lambda item: item["filename"])
    return {"schema_version": _CATALOG_SCHEMA_VERSION, "items": normalized_items}


def _catalog_items_with_file_fingerprints(
    wd: str,
    *,
    sync_metadata: bool = False,
) -> list[dict[str, Any]]:
    catalog_dir = _landuse_user_defined_dir(wd)
    catalog_dir.mkdir(parents=True, exist_ok=True)

    metadata = _read_catalog_metadata(wd)
    metadata_items = metadata.get("items", [])
    by_filename = {
        str(item["filename"]): dict(item)
        for item in metadata_items
        if isinstance(item, dict) and "filename" in item
    }

    synced_items: list[dict[str, Any]] = []
    for file_path in sorted(catalog_dir.glob("*.man"), key=lambda candidate: candidate.name.lower()):
        filename = file_path.name.lower()
        metadata_item = by_filename.pop(filename, {})
        description = str(metadata_item.get("description") or "").strip() or _catalog_default_description(filename)
        uploaded_at = str(metadata_item.get("uploaded_at") or "").strip() or _utc_iso_timestamp()
        synced_items.append(
            {
                "filename": filename,
                "description": description,
                "uploaded_at": uploaded_at,
                "size_bytes": int(file_path.stat().st_size),
                "sha256": _sha256_path(file_path),
            }
        )

    if sync_metadata:
        _write_json_atomic(
            _landuse_catalog_path(wd),
            {"schema_version": _CATALOG_SCHEMA_VERSION, "items": [
                {
                    "filename": item["filename"],
                    "description": item["description"],
                    "uploaded_at": item["uploaded_at"],
                }
                for item in synced_items
            ]},
        )
    return synced_items


def _persist_catalog_items(wd: str, items: list[dict[str, Any]]) -> None:
    normalized = []
    for raw_item in items:
        filename = _safe_catalog_filename(str(raw_item.get("filename")))
        description = str(raw_item.get("description") or "").strip() or _catalog_default_description(filename)
        uploaded_at = str(raw_item.get("uploaded_at") or "").strip() or _utc_iso_timestamp()
        normalized.append(
            {
                "filename": filename,
                "description": description,
                "uploaded_at": uploaded_at,
            }
        )
    normalized.sort(key=lambda item: item["filename"])
    _write_json_atomic(
        _landuse_catalog_path(wd),
        {"schema_version": _CATALOG_SCHEMA_VERSION, "items": normalized},
    )


def _read_upload_bytes_with_limit(upload_stream: Any, *, max_bytes: int) -> bytes:
    stream = upload_stream
    if hasattr(stream, "seek"):
        stream.seek(0)
    payload = stream.read(max_bytes + 1)
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if len(payload) > max_bytes:
        raise ValueError(f"Archive exceeds {max_bytes} byte limit")
    return payload


def _is_macos_archive_metadata_sidecar(normalized_path: PurePosixPath) -> bool:
    if normalized_path.parts and normalized_path.parts[0] == _MACOS_ARCHIVE_METADATA_DIR:
        return True
    name = normalized_path.name
    return name.startswith("._") or name.lower() == ".ds_store"


def _man_archive_member_policy(_member: Any, normalized_path: PurePosixPath) -> None:
    if _is_macos_archive_metadata_sidecar(normalized_path):
        return

    if normalized_path.as_posix() != normalized_path.name:
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive members must be at the archive root.",
            details=f"Entry '{normalized_path.as_posix()}' is nested.",
            status_code=400,
        )

    safe_name = _safe_catalog_filename(normalized_path.name)
    if safe_name != normalized_path.name.lower():
        raise ShapeConverterError(
            code="invalid_archive",
            message="Archive member filenames must be safe and normalized.",
            details=f"Entry '{normalized_path.name}' normalizes to '{safe_name}'.",
            status_code=400,
        )


def _validate_management_file(path: Path) -> None:
    try:
        read_management(str(path))
    except Exception as exc:
        # Validation boundary: parser failures are surfaced as user-facing 400s.
        raise ValueError(f"Invalid management file '{path.name}': {exc}") from exc


def _install_uploaded_managements(
    *,
    target_dir: Path,
    staged_files: list[Path],
    replace: bool,
) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    operation_id = uuid4().hex
    staged_targets: list[tuple[Path, Path]] = []

    for source_path in staged_files:
        filename = _safe_catalog_filename(source_path.name)
        incoming_path = target_dir / f".incoming-{operation_id}-{filename}"
        shutil.copyfile(source_path, incoming_path)
        staged_targets.append((incoming_path, target_dir / filename))

    conflicts = [target.name for _incoming, target in staged_targets if target.exists()]
    if conflicts and not replace:
        for incoming, _target in staged_targets:
            incoming.unlink(missing_ok=True)
        conflict_csv = ", ".join(sorted(conflicts))
        raise FileExistsError(
            f"Management file(s) already exist: {conflict_csv}. Use replace=true to overwrite."
        )

    backups: dict[Path, Path] = {}
    installed_targets: list[Path] = []
    try:
        for incoming_path, target_path in staged_targets:
            if target_path.exists():
                backup_path = target_dir / f".backup-{operation_id}-{target_path.name}"
                os.replace(target_path, backup_path)
                backups[target_path] = backup_path

            os.replace(incoming_path, target_path)
            installed_targets.append(target_path)
    except Exception:
        for incoming_path, _target_path in staged_targets:
            incoming_path.unlink(missing_ok=True)

        for target_path in reversed(installed_targets):
            target_path.unlink(missing_ok=True)

        for target_path, backup_path in backups.items():
            if backup_path.exists():
                os.replace(backup_path, target_path)
        raise
    else:
        for backup_path in backups.values():
            backup_path.unlink(missing_ok=True)

    return sorted(target_path.name for target_path in installed_targets)


def _sorted_mapping_keys(mapping: Mapping[str, Mapping[str, Any]]) -> list[str]:
    def _sort_token(raw: str) -> tuple[int, Any]:
        token = str(raw)
        try:
            return (0, int(token))
        except ValueError:
            return (1, token)

    return sorted((str(key) for key in mapping.keys()), key=_sort_token)


def _candidate_management_index(
    *,
    mapping_dict: Mapping[str, Mapping[str, Any]],
    catalog_items: list[dict[str, Any]],
    catalog_dir: Path,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    for key in _sorted_mapping_keys(mapping_dict):
        entry = mapping_dict[key]
        management_file = str(entry.get("ManagementFile") or "").strip()
        if not management_file:
            continue

        soil_file = entry.get("SoilFile")
        if soil_file == "":
            soil_file = None

        management_dir = str(entry.get("ManagementDir") or WEPPPY_MAN_DIR)
        index.setdefault(
            management_file,
            {
                "management_file": management_file,
                "management_dir": management_dir,
                "soil_file": soil_file,
                "description": str(entry.get("Description") or "").strip(),
                "source": "mapping",
            },
        )

    for item in catalog_items:
        management_file = str(item["filename"])
        index[management_file] = {
            "management_file": management_file,
            "management_dir": str(catalog_dir),
            "soil_file": None,
            "description": str(item.get("description") or "").strip(),
            "source": "user_defined",
        }

    return index


def _build_landuse_map_snapshot_payload(landuse: Landuse, wd: str) -> dict[str, Any]:
    mapping_reference = landuse._resolve_effective_mapping_reference(landuse.mapping)  # type: ignore[attr-defined]
    mapping_dict = load_map(mapping_reference)
    catalog_dir = _landuse_user_defined_dir(wd)
    catalog_items = _catalog_items_with_file_fingerprints(wd)
    management_index = _candidate_management_index(
        mapping_dict=mapping_dict,
        catalog_items=catalog_items,
        catalog_dir=catalog_dir,
    )

    rows: list[dict[str, Any]] = []
    hash_rows: list[dict[str, Any]] = []
    for key in _sorted_mapping_keys(mapping_dict):
        entry = dict(mapping_dict[key])
        row_key = str(entry.get("Key", key))
        management_file = str(entry.get("ManagementFile") or "").strip()
        row = {
            "key": row_key,
            "description": str(entry.get("Description") or ""),
            "disturbed_class": str(entry.get("DisturbedClass") or ""),
            "management_file": management_file,
            "soil_file": str(entry.get("SoilFile") or ""),
        }
        rows.append(row)
        hash_rows.append(
            {
                "key": row_key,
                "management_file": management_file,
            }
        )

    options = sorted(
        (
            {
                "management_file": token,
                "description": str(metadata.get("description") or ""),
                "source": str(metadata.get("source") or "mapping"),
            }
            for token, metadata in management_index.items()
        ),
        key=lambda option: option["management_file"].lower(),
    )

    lookup_sha256 = hashlib.sha256(
        json.dumps(hash_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "rows": rows,
        "management_options": options,
        "lookup_sha256": lookup_sha256,
        "mapping_reference": mapping_reference,
    }


def _snapshot_payload_for_client(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    response_payload = dict(snapshot)
    response_payload.pop("mapping_reference", None)
    return response_payload


def _landuse_mapping_error_message(exc: LanduseCustomMappingError | ManagementMapLoadError) -> str:
    if isinstance(exc, ManagementMapLoadError):
        code = str(getattr(exc, "code", "") or "").strip().lower()
        if code == "management_map_missing":
            return "Management map file does not exist"
        if code == "management_map_invalid_json":
            return "Management map file is not valid JSON"
        if code == "management_map_invalid_shape":
            return "Management map payload is invalid"
        return "Failed to load management map"
    return str(exc)


def _landuse_mapping_error_response(exc: LanduseCustomMappingError | ManagementMapLoadError) -> Response:
    code = getattr(exc, "code", _LANDUSE_MAP_INVALID_CODE)
    details: dict[str, Any] = {}
    raw_details = getattr(exc, "details", None)
    if isinstance(raw_details, dict):
        details.update(raw_details)
    details.pop("map_path", None)
    return error_factory(_landuse_mapping_error_message(exc), status_code=400, code=code, details=details or None)


def _restore_landuse_map_override_state(
    *,
    landuse: Landuse,
    wd: str,
    previous_relpath: str | None,
    previous_override_bytes: bytes | None,
) -> None:
    override_path = _landuse_mapping_override_path(wd)
    if previous_override_bytes is None:
        override_path.unlink(missing_ok=True)
    else:
        _write_bytes_atomic(override_path, previous_override_bytes)

    with landuse.locked():
        # Direct assignment avoids nested lock usage from nodb_setter wrappers.
        landuse._custom_mapping_relpath = previous_relpath


def _coerce_landuse_code(value: Any) -> str:
    if value in (None, ''):
        raise ValueError('landuse missing')
    try:
        return str(int(value))
    except (TypeError, ValueError) as exc:
        raise ValueError('landuse must be an integer value') from exc


def _iter_values(raw: Any) -> Iterable[Any]:
    if isinstance(raw, str):
        yield from (segment.strip() for segment in raw.split(','))
        return
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        for item in raw:
            if item in (None, ''):
                continue
            if isinstance(item, str):
                yield from (segment.strip() for segment in item.split(','))
            else:
                yield item
        return
    if raw not in (None, ''):
        yield raw


def _coerce_topaz_ids(raw: Any) -> List[str]:
    candidate_ids: List[str] = []
    for value in _iter_values(raw):
        if value in (None, ''):
            continue
        try:
            candidate_ids.append(str(int(value)))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'invalid topaz id: {value!r}') from exc
    return candidate_ids


def build_landuse_report_context(landuse: Landuse) -> Dict[str, object]:
    """Prepare dataset options and report rows for landuse summaries."""
    dataset_source = getattr(landuse, "available_datasets", [])
    datasets = [
        dataset
        for dataset in dataset_source
        if getattr(dataset, "kind", None) == "mapping"
    ]

    dataset_options: List[Tuple[str, str]] = []
    for dataset in datasets:
        key = getattr(dataset, "key", "")
        label = getattr(dataset, "label", key)
        description = getattr(dataset, "description", "")
        management_file = getattr(dataset, "management_file", "")
        if description and management_file:
            label = f"{description} ({management_file})"
        dataset_options.append((key, label))

    prefix_order = sorted(datasets, key=lambda ds: len(ds.key), reverse=True)
    report_rows: List[Dict[str, object]] = []

    report_source = getattr(landuse, "report", [])
    if isinstance(report_source, Mapping):
        report_entries = list(report_source.get("rows", []))
    else:
        try:
            report_entries = list(report_source)
        except TypeError:
            report_entries = []

    for entry in report_entries:
        row = dict(entry)
        key_str = str(row.get('key', ''))
        selected_dataset = next((ds for ds in prefix_order if key_str.startswith(ds.key)), None)
        row['_dataset'] = selected_dataset
        row['_dataset_key'] = selected_dataset.key if selected_dataset else None
        report_rows.append(row)

    return {
        'dataset_options': dataset_options,
        'coverage_percentages': getattr(landuse, "coverage_percentages", ()),
        'report_rows': report_rows,
    }


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/')
@authorize_and_handle_with_exception_factory
def query_landuse(runid: str, config: str) -> Response:
    """Return the landuse domain metadata dictionary."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).domlc_d)


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/subcatchments')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_landuse_subcatchments(runid: str, config: str) -> Response:
    """Return subcatchment summary table for landuse."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).subs_summary)


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/channels')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/channels/')
@authorize_and_handle_with_exception_factory
def query_landuse_channels(runid: str, config: str) -> Response:
    """Return channel summary table for landuse."""
    wd = get_wd(runid)
    return jsonify(Landuse.getInstance(wd).chns_summary)


@landuse_bp.route('/runs/<string:runid>/<config>/report/landuse')
@landuse_bp.route('/runs/<string:runid>/<config>/report/landuse/')
@authorize_and_handle_with_exception_factory
@requires_cap(gate_reason="Complete verification to view landuse reports.")
def report_landuse(runid: str, config: str) -> Response:
    """Render the HTML landuse report for the current run."""
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)

    try:
        # Read a detached snapshot so cross-worker singleton cache drift cannot
        # serve stale mapping rows right after a successful modify request.
        landuse = Landuse.load_detached(wd, allow_nonexistent=True)
        if landuse is None:
            landuse = Landuse.getInstance(wd)
        landuseoptions = landuse.landuseoptions
        report_context = build_landuse_report_context(landuse)
        disturbed_preview_available = "disturbed" in tuple(getattr(landuse, "mods", ()))

        response = make_response(
            render_template(
                'reports/landuse.htm',
                runid=runid,
                config=config,
                landuse=landuse,
                landuseoptions=landuseoptions,
                dataset_options=report_context['dataset_options'],
                coverage_percentages=report_context['coverage_percentages'],
                report=report_context['report_rows'],
                disturbed_preview_available=disturbed_preview_available,
                disturbed_preview_textures=_DISTURBED_PREVIEW_TEXTURES,
            )
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/landuse_bp.py:260", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Reporting landuse failed', runid=runid)


@landuse_bp.route("/runs/<string:runid>/<config>/landuse-user-defined")
@authorize_and_handle_with_exception_factory
def view_landuse_user_defined(runid: str, config: str) -> Response:
    """Render the run-scoped user-defined landuse management catalog page."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)

    try:
        catalog_items = _catalog_items_with_file_fingerprints(wd)
    except ValueError as exc:
        return error_factory(str(exc), status_code=400, code="INVALID_RUN_PATH")
    quoted_runid = quote(runid, safe="")
    quoted_config = quote(config, safe="")

    response = make_response(
        render_template(
            "controls/landuse_user_defined.htm",
            runid=runid,
            config=config,
            catalog_items=catalog_items,
            list_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-user-defined/catalog",
            upload_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-user-defined/upload",
            delete_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-user-defined/delete",
            update_description_url=(
                f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-user-defined/update-description"
            ),
            session_token_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/session-token",
        )
    )
    return _set_no_store_headers(response)


@landuse_bp.route("/runs/<string:runid>/<config>/landuse-map")
@authorize_and_handle_with_exception_factory
def view_landuse_map(runid: str, config: str) -> Response:
    """Render the run-scoped landuse management mapping editor page."""
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    landuse = Landuse.getInstance(wd)

    try:
        snapshot = _build_landuse_map_snapshot_payload(landuse, wd)
    except (LanduseCustomMappingError, ManagementMapLoadError) as exc:
        return _landuse_mapping_error_response(exc)
    except ValueError as exc:
        return error_factory(str(exc), status_code=400, code="INVALID_RUN_PATH")
    client_snapshot = _snapshot_payload_for_client(snapshot)
    quoted_runid = quote(runid, safe="")
    quoted_config = quote(config, safe="")

    response = make_response(
        render_template(
            "controls/landuse_map.htm",
            runid=runid,
            config=config,
            snapshot=client_snapshot,
            snapshot_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-map/snapshot",
            save_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-map/save",
            clear_override_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/landuse-map/clear-override",
            session_token_url=f"/rq-engine/api/runs/{quoted_runid}/{quoted_config}/session-token",
        )
    )
    return _set_no_store_headers(response)


@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments')
@landuse_bp.route('/runs/<string:runid>/<config>/query/landuse/cover/subcatchments/')
@authorize_and_handle_with_exception_factory
def query_landuse_cover_subcatchments(runid: str, config: str) -> Response:
    """Return coverage summaries for hillslope landuse."""
    wd = get_wd(runid)
    d = Landuse.getInstance(wd).hillslope_cancovs
    return jsonify(d)
