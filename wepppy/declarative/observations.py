"""Shared acquisition-boundary observations, independent of the operator engine."""

import logging
import math
import os
import platform
import re
import time
from uuid import uuid4

from .records import checkpoint, digest, guard, marker, project_identity, read, utcnow, write

LOGGER = logging.getLogger(__name__)


def start_observation(ron, job):
    admission = marker(ron.wd)
    try:
        return DemObservation(ron, job)
    except Exception as exc:  # broad-except: optional diagnostic boundary
        # Optional observation boundary; declarative evidence remains mandatory.
        LOGGER.error("Unable to start DEM observation runid=%s error_type=%s", ron.runid, type(exc).__name__)
        if admission:
            raise
        return None


def runtime(job):
    return {"pod_uid": os.environ.get("DECLARATIVE_POD_UID"),
            "pod_name": os.environ.get("DECLARATIVE_POD_NAME"),
            "namespace": os.environ.get("DECLARATIVE_NAMESPACE"),
            "container": os.environ.get("DECLARATIVE_CONTAINER"),
            "worker_name": getattr(job, "worker_name", None),
            "job_id": getattr(job, "id", None), "queue": getattr(job, "origin", None),
            "platform": f"{platform.system().lower()}/{platform.machine()}",
            "registry_identity": "unknown"}


def raster_summary(path, *, expected_grid=None):
    import numpy as np
    import rasterio
    with rasterio.open(path) as dataset:
        if expected_grid is not None:
            cellsize = expected_grid["cellsize"]
            if (dataset.crs is None or dataset.crs.to_epsg() != expected_grid["srid"]
                    or [dataset.height, dataset.width] != expected_grid["shape"]
                    or dataset.transform.a != cellsize or dataset.transform.e != -cellsize
                    or dataset.transform.b != 0 or dataset.transform.d != 0
                    or abs(dataset.transform.c - expected_grid["origin"][0]) > cellsize / 2
                    or abs(dataset.transform.f - expected_grid["origin"][1]) > cellsize / 2):
                raise ValueError("DEM grid does not match the requested map")
        data = dataset.read(1, masked=True)
        values = data.compressed()
        if dataset.crs is None or not values.size or not np.isfinite(values).all():
            raise ValueError("DEM has no valid finite elevation content or CRS")
        nodata = dataset.nodata
        return {"path": "dem/dem.tif", "sha256": digest(path),
                "crs": dataset.crs.to_string(), "bounds": list(dataset.bounds),
                "transform": list(dataset.transform), "shape": [dataset.height, dataset.width],
                "nodata": nodata if nodata is None or math.isfinite(nodata) else "nonfinite",
                "valid_cells": int(values.size), "minimum": float(values.min()),
                "maximum": float(values.max()), "sample": float(values[len(values) // 2])}


class DemObservation:
    def __init__(self, ron, job):
        self.wd = ron.wd
        self.admission = marker(ron.wd)
        self.identity = project_identity(ron.wd)
        self.attempt_id = self.admission["attempt_id"] if self.admission else str(uuid4())
        self.started = time.monotonic()
        self.record = {
            "schema": "dem-observation-v1", "operation": "fetch_dem_rq",
            "attempt_id": self.attempt_id, "job_id": getattr(job, "id", None),
            "runid": ron.runid, "node": "dem", "disposition": "executed",
            "started_at": utcnow(), "runtime": runtime(job),
            "inputs": {"source": ron.dem_db if re.fullmatch(
                r"(?:ned1|ned13)/[0-9]{4}|(?:copernicus|opentopo)://[A-Za-z0-9_-]+", ron.dem_db
            ) else "unrecorded", "extent": list(ron.map.extent),
                       "center": list(ron.map.center), "zoom": ron.map.zoom,
                       "cellsize": ron.map.cellsize, "evidence": "acquisition-boundary"},
        }
        if self.admission:
            self.record["inputs"]["grid"] = {
                "srid": int(ron.map.srid), "shape": [ron.map.num_rows, ron.map.num_cols],
                "origin": [ron.map.ul_x, ron.map.ul_y], "cellsize": ron.map.cellsize,
            }

    def finish(self, ron, *, succeeded):
        """Diagnostic errors are isolated only for ordinary on-demand tasks."""
        import rasterio
        try:
            self.record.update(ended_at=utcnow(), outcome="succeeded" if succeeded else "failed",
                               acquisition_seconds=time.monotonic() - self.started)
            started = time.monotonic()
            evidence_error = None
            if succeeded:
                try:
                    self.record["output"] = raster_summary(ron.dem_fn, expected_grid=self.record["inputs"].get("grid"))
                except (ValueError, OSError, rasterio.errors.RasterioError) as exc:
                    evidence_error = exc
                    self.record.update(outcome="failed", error={"code": "invalid_dem_evidence",
                                       "message": "DEM semantic readback failed"})
            self.record["hash_readback_seconds"] = time.monotonic() - started
            with guard(self.wd):
                if marker(self.wd) != self.admission or project_identity(self.wd) != self.identity:
                    raise ValueError("Admission changed during acquisition")
                path = f"attempts/{self.attempt_id}.json"
                write(self.wd, "provenance/" + path, self.record, exclusive=True)
                paths = [path] + (["declarative.json"] if self.admission else [])
                commit = checkpoint(self.wd, self.attempt_id, paths)
                if self.admission:
                    state = read(self.wd, "provenance/build.json")
                    state["checkpoint"] = commit
                    write(self.wd, "provenance/build.json", state)
            if evidence_error is not None:
                raise evidence_error
            return commit
        except Exception as exc:  # broad-except: optional diagnostic publication boundary
            # Optional diagnostic publication boundary: never alter ordinary science.
            LOGGER.error("DEM provenance publication failed runid=%s attempt=%s error_type=%s",
                         self.record["runid"], self.attempt_id, type(exc).__name__)
            if self.admission:
                raise
            return None
