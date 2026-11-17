"""Retained Roads parameterization materialization and execution provenance."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from wepppy.nodb.mods.roads import parameterization as roads_parameterization


def _saved_parameterization_state(self):
    # A persisted null is malformed, distinct from an absent legacy key.
    state = getattr(self, "_parameterization", None)
    return {} if state is None and "_parameterization" in self.__dict__ else state


def _parameterization_template_path(self, directory: str, name: str) -> Path:
    state = self._saved_parameterization_state()
    if state is None:
        return Path(self.roads_legacy_templates_dir) / directory / name
    root = getattr(self, "_parameterization_runtime_templates", None)
    if root is None:
        self._ensure_roads_dirs()
        root = roads_parameterization.materialize_baseline(state, Path(self.roads_runs_dir))
        self._parameterization_runtime_templates = root
    return Path(root) / directory / name


def _apply_parameterization_to_soil(self, path, template_path, traffic, ofe_order):
    state = self._saved_parameterization_state()
    if state is None:
        return
    record = roads_parameterization.apply_soil_overrides(
        path, state, ofe_order, template_name=Path(template_path).name, traffic=traffic
    )
    cache = getattr(self, "_parameterization_runtime_readbacks", None)
    if cache is None:
        cache = self._parameterization_runtime_readbacks = {}
    cache[str(Path(path))] = record


def _record_parameterization_inputs(self, soil_path, slope_path, management_path):
    readbacks = getattr(self, "_parameterization_runtime_readbacks", {})
    provenance = readbacks.get(str(Path(soil_path)))
    if provenance is None:
        raise ValueError("Roads native soil has no parameterization readback.")
    files = []
    for path in (soil_path, slope_path, management_path):
        path = Path(path)
        if not path.is_file() or not path.resolve().is_relative_to(Path(self.wd).resolve()):
            raise ValueError(f"Roads parameterization input is missing or outside the run: {path.name}")
        files.append({"relpath": os.path.relpath(path, self.wd),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    provenance["input_files"] = files
    # Visible even if native execution fails before the manifest is written.
    Path(soil_path).with_suffix(".parameterization.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8"
    )


def _attach_parameterization_records(self, records):
    state = roads_parameterization.validate_state(self._saved_parameterization_state())
    signature = roads_parameterization.configuration_hash(state)
    readbacks = getattr(self, "_parameterization_runtime_readbacks", {})
    for record in records:
        run_id = record.get("segment_run_id")
        matched = [(path, value) for path, value in readbacks.items()
                   if Path(path).name.startswith(f"p{run_id}.")]
        if matched:
            _, provenance = matched[0]
            provenance = json.loads(json.dumps(provenance))
            if record.get("status") == "completed":
                files = provenance.get("input_files", [])
                if not provenance.get("ofes") or {Path(row["relpath"]).suffix for row in files} != {".sol", ".slp", ".man"}:
                    raise ValueError("Completed Roads profile lacks complete native parameterization inputs.")
                for row in files:
                    path = Path(self.wd) / row["relpath"]
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                        raise ValueError("Completed Roads parameterization inputs changed after readback.")
            record["parameterization"] = provenance
        else:
            if record.get("status") == "completed":
                raise ValueError("Completed Roads profile lacks native parameterization readback.")
            record["parameterization"] = {
                "baseline_id": state["baseline"]["id"],
                "configuration_hash": signature,
                "ofes": [], "input_files": [],
                "reason": record.get("reason") or "native_inputs_not_assembled",
            }


def _resolve_legacy_soil_template_path(self, *, design: str, surface: str, soil_texture: str) -> Path:
    if design == "inslope_rd":
        tau_value = "10"
    elif design in {"inslope_bd", "outslope_rutted"} and surface == "paved":
        tau_value = "1"
    else:
        tau_value = "2"

    surface_prefix = "p" if surface == "paved" else "g"
    template_name = f"3{surface_prefix}{soil_texture}{tau_value}.sol"
    template_path = self._parameterization_template_path("soils", template_name)
    if not template_path.exists():
        raise FileNotFoundError(
            f"Roads soil template is missing: {template_path} "
            f"(design={design}, surface={surface}, soil_texture={soil_texture})."
        )
    return template_path


def _resolve_legacy_management_template_path(self, *, traffic: str) -> Path:
    template_name = "3inslopen.man" if traffic == "none" else "3inslope.man"
    template_path = self._parameterization_template_path("managements", template_name)
    if not template_path.exists():
        raise FileNotFoundError(
            f"Roads management template is missing: {template_path} (traffic={traffic})."
        )
    return template_path
