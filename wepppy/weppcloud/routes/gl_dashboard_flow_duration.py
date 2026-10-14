"""Read-only source ownership and outlet metadata for the daily duration graph."""
from __future__ import annotations

import csv
import io
import json
import math
import duckdb
import logging
from pathlib import Path

from wepppy.nodb.core import Watershed
from wepppy.topo.peridot.peridot_runner import read_network

LOGGER = logging.getLogger(__name__)
OBSERVED_MAX_BYTES = 16 * 1024 * 1024
OBSERVED_MAX_ROWS = 100_000

SOURCES = {
    "hillslope": "wepp/output/interchange/totalwatsed3.parquet",
    "outlet": "wepp/output/interchange/chanwb.parquet",
}


def _owned_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Daily source is missing or outside its scenario")
    return path


def _source_status(root: Path, relative: str) -> dict:
    try:
        expected = _owned_file(root, relative)
        catalog_path = root / "_query_engine/catalog.json"
        if catalog_path.exists() or catalog_path.is_symlink():
            catalog_file = _owned_file(root, "_query_engine/catalog.json")
            catalog = json.loads(catalog_file.read_text())
            if not isinstance(catalog, dict) or not isinstance(catalog.get("root"), str):
                raise ValueError("Invalid daily-source catalog")
            if Path(catalog["root"]).resolve() != root:
                raise ValueError("Daily-source catalog belongs to another run")
            entries = catalog.get("files")
            if not isinstance(entries, list):
                raise ValueError("Invalid daily-source catalog entries")
            matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("path") == relative]
            if len(matches) != 1:
                raise ValueError("Daily-source catalog needs refresh")
            physical = matches[0].get("fs_path") or relative
            if not isinstance(physical, str) or (root / physical).resolve() != expected:
                raise ValueError("Daily-source catalog points to another file")
        return {"available": True}
    except (OSError, ValueError, RuntimeError) as exc:
        LOGGER.info("Flow-duration source unavailable at %s: %s", root / relative, exc)
        return {"available": False, "reason": str(exc) if isinstance(exc, ValueError) else "Daily source cannot be read"}


def _observed_status(project: Path) -> dict:
    """Read the normalized upload without model-fit writes or catalog activation."""
    candidate = project / "observed/observed.csv"
    try:
        if not candidate.resolve().is_relative_to(project):
            raise ValueError("Observed CSV is outside this project")
        if not candidate.exists() and not candidate.is_symlink():
            return {"present": False, "available": False}
        csv_path = _owned_file(project, "observed/observed.csv")
        with csv_path.open("rb") as stream:
            raw = stream.read(OBSERVED_MAX_BYTES + 1)
        if len(raw) > OBSERVED_MAX_BYTES:
            raise ValueError("Observed CSV exceeds 16 MiB; reduce the upload and reload")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        required = {"Year", "Month", "Day", "Julian", "Streamflow (mm)"}
        fields = reader.fieldnames or []
        if not required.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("Observed CSV needs unique date and Streamflow (mm) columns")
        records = []
        for row in reader:
            if len(records) >= OBSERVED_MAX_ROWS:
                raise ValueError("Observed CSV exceeds 100,000 daily records; reduce the upload and reload")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Observed CSV has a malformed row")
            try:
                julian = int(row["Julian"]) + 1  # Observed persists zero-based Julian.
            except ValueError as exc:
                raise ValueError("Observed CSV has an invalid Julian date") from exc
            records.append({
                "year": row["Year"], "month": row["Month"], "day": row["Day"],
                "julian": julian, "flow": row["Streamflow (mm)"].strip() or None,
            })
        if not records:
            raise ValueError("Observed CSV has no daily records")
        area_path = _owned_file(project, SOURCES["hillslope"])
        with duckdb.connect() as connection:
            area_type = connection.execute(
                'DESCRIBE SELECT "Area" FROM read_parquet(?)', [str(area_path)]
            ).fetchone()[1]
            if area_type == "BOOLEAN":
                raise ValueError("Observed discharge needs a numeric watershed area")
            # Match Observed model-fit: convert before MAX, including legacy numeric strings.
            area = connection.execute(
                'SELECT MAX(CAST("Area" AS DOUBLE)) FROM read_parquet(?)', [str(area_path)]
            ).fetchone()[0]
        if area is None or not math.isfinite(area) or area <= 0:
            raise ValueError("Observed discharge needs a finite positive watershed area")
        for row in records:
            row["area"] = str(float(area))
        return {"present": True, "available": True, "records": records}
    except (OSError, ValueError, RuntimeError, csv.Error, duckdb.Error) as exc:
        LOGGER.warning("Observed flow-duration source unavailable at %s: %s", candidate, exc)
        reason = str(exc) if isinstance(exc, ValueError) else "Observed CSV or watershed area cannot be read"
        return {"present": True, "available": False, "reason": reason}


def _outlet_ids(root: Path, project: Path) -> dict:
    for relative in ("watershed.nodb", "watershed", "watershed/hillslopes.parquet", "watershed/channels.parquet"):
        candidate = root / relative
        if not candidate.resolve().is_relative_to(project):
            raise ValueError("Watershed metadata is outside this project")
    watershed = Watershed.getInstance(str(root))
    translator = watershed.translator_factory()
    channels = {int(key.split("_", 1)[1]) for key in translator.chn_ids}
    outlet = watershed.outlet_top_id
    if outlet is not None:
        outlet = int(outlet)
    elif len(channels) == 1:
        outlet = next(iter(channels))
    else:
        network_path = (root / "watershed/network.txt").resolve()
        if not network_path.is_relative_to(project) or not network_path.is_file():
            raise ValueError("Watershed topology is unavailable")
        network = read_network(str(network_path))
        upstream = {value for values in network.values() for value in values if value in channels}
        roots = channels - upstream
        if len(roots) != 1 or not roots.issubset(network):
            raise ValueError("Watershed outlet topology is unavailable or ambiguous")
        outlet = next(iter(roots))
    if outlet not in channels:
        raise ValueError("Watershed outlet is not a registered channel")
    return {"channelId": translator.chn_enum(top=outlet), "elementId": translator.wepp(top=outlet)}


def flow_duration_context(wd: str, scenarios: list | None, output_scope: str, *, query_run_is_child: bool = False) -> dict:
    if output_scope != "baseline":
        return {"reason": "Flow duration is available for baseline output scope only", "scenarios": {}}
    base = Path(wd).resolve()
    project = base
    query_scenario = ""
    # Omni child views share parent topology, as do Query Engine child contexts.
    # Recognize only the established canonical lineage, never an arbitrary ancestor.
    if (base.parent.name == "scenarios" and base.parent.parent.name == "omni"
            and base.parent.parent.parent.name == "_pups"):
        project = base.parents[3]
        if not query_run_is_child:
            query_scenario = base.relative_to(project).as_posix()
    results = {}
    for relative in [""] + [scenario["path"] for scenario in scenarios or []]:
        try:
            root = (base / relative).resolve()
            contained = root.is_relative_to(base) and (not relative or root == base / relative)
        except (OSError, RuntimeError):
            contained = False
        if not contained:
            results[relative] = {source: {"available": False, "reason": "Scenario is outside this project"} for source in SOURCES}
            continue
        status = {source: _source_status(root, path) for source, path in SOURCES.items()}
        if status["outlet"]["available"]:
            try:
                status["outlet"].update(_outlet_ids(root, project))
            except (OSError, ValueError, KeyError, TypeError, RuntimeError, AssertionError, AttributeError, duckdb.Error) as exc:
                LOGGER.warning("Flow-duration outlet unavailable for %s: %s", root, exc)
                status["outlet"] = {"available": False, "reason": "Watershed outlet metadata is unavailable"}
        results[relative] = status
    return {"scenarios": results, "observed": _observed_status(project), "queryScenarioPath": query_scenario,
            "activeScenarioName": base.name if project != base else None}
