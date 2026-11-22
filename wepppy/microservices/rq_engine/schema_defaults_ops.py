"""Assemble the run-scoped operation catalog from per-domain discovery documents."""

from __future__ import annotations

from typing import Any

from . import schema_defaults_ops_inputs as inputs
from . import schema_defaults_ops_landuse as landuse
from . import schema_defaults_ops_metadata as metadata
from . import schema_defaults_ops_models as models
from . import schema_defaults_ops_project as project
from . import schema_defaults_ops_uploads as uploads
from . import schema_defaults_ops_watershed as watershed
from .openapi import rq_operation_id
from .schema_defaults_geospatial import _geospatial_payload
from .schema_defaults_runtime import RuntimeState


def _build_run_operations(runtime: RuntimeState) -> dict[str, dict[str, Any]]:
    geospatial_defaults = _geospatial_payload(runtime).get("recommended_defaults", {})
    documents = (
        metadata.list_controllers(runtime),
        landuse.get_landuse_state(runtime),
        metadata.geospatial_metadata(runtime),
        metadata.get_controller_schema(runtime),
        metadata.get_controller_hints(runtime),
        metadata.get_controller_templates(runtime),
        metadata.list_run_endpoints(runtime),
        metadata.get_run_endpoint_schema(runtime),
        metadata.get_run_endpoint_defaults(runtime),
        metadata.get_run_endpoint_errors(runtime),
        metadata.get_pipeline(runtime),
        metadata.get_readiness(runtime),
        metadata.get_outputs(runtime),
        watershed.fetch_dem_and_build_channels(runtime, geospatial_defaults),
        watershed.set_outlet(runtime, geospatial_defaults),
        watershed.build_subcatchments_and_abstract_watershed(runtime),
        inputs.build_climate(runtime),
        landuse.build_landuse(runtime),
        landuse.set_landuse_mode(runtime),
        landuse.set_landuse_db(runtime),
        landuse.modify_landuse_coverage(runtime),
        landuse.modify_landuse_mapping(runtime),
        landuse.get_landuse_user_defined_catalog(runtime),
        landuse.upload_landuse_user_defined_managements(runtime),
        landuse.delete_landuse_user_defined_management(runtime),
        landuse.update_landuse_user_defined_management_description(runtime),
        landuse.get_landuse_map_snapshot(runtime),
        landuse.save_landuse_map(runtime),
        landuse.clear_landuse_map_override(runtime),
        landuse.modify_landuse(runtime),
        inputs.build_soils(runtime),
        models.prep_wepp_watershed(runtime),
        models.run_wepp(runtime),
        models.run_wepp_watershed(runtime),
        models.build_rusle(runtime),
        uploads.upload_dem(runtime),
        uploads.upload_cli(runtime),
        uploads.upload_cover_transform(runtime),
        project.issue_session_token(runtime),
        project.fork_project(runtime),
    )
    operations = {doc["descriptor"]["operation_id"]: doc for doc in documents}
    active_mod_tokens = {mod.lower() for mod in runtime.active_mods}
    if not active_mod_tokens.intersection({"disturbed", "baer"}):
        operations.pop(rq_operation_id("build_rusle"))
    if runtime.states.get("sbs_upload_supported", False):
        operations[rq_operation_id("upload_sbs")] = uploads.upload_sbs(runtime)

    catalog_defaults = operations[rq_operation_id("list_run_endpoints")]["defaults"]
    catalog_defaults["defaults_context"]["operation_count"] = len(operations)
    return {key: operations[key] for key in sorted(operations, key=str.casefold)}
