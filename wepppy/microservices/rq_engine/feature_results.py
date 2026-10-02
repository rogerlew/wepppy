"""Identify restricted execution for cancellation; retained results are shareable."""

_TASK_FEATURES = {
    "fetch_and_analyze_openet_ts_rq": "openet_ts",
    "run_omni_contrasts_rq": "omni_contrasts",
    "run_omni_contrast_rq": "omni_contrasts",
    "delete_omni_contrasts_rq": "omni_contrasts",
    "_finalize_omni_contrasts_rq": "omni_contrasts",
    "run_path_cost_effective_rq": "path_ce",
    "build_ag_fields_subfields_rq": "ag_fields",
    "process_ag_fields_plant_db_rq": "ag_fields",
    "run_ag_fields_wepp_rq": "ag_fields",
    "run_ag_fields_watershed_rq": "ag_fields",
    "finalize_ag_fields_watershed_suite_rq": "ag_fields",
    "run_ag_fields_watershed_suite_rq": "ag_fields",
    "run_batch_rq": "batch_runner",
    "delete_batch_rq": "batch_runner",
    "run_batch_hillslopes_rq": "batch_runner",
    "run_batch_watershed_rq": "batch_runner",
    "_final_batch_complete_rq": "batch_runner",
    "run_culvert_batch_rq": "culvert_runner",
    "run_culvert_run_rq": "culvert_runner",
    "run_culvert_batch_finalize_rq": "culvert_runner",
    "_final_culvert_batch_complete_rq": "culvert_runner",
}


def restricted_job_feature(node):
    """Classify the task name, never arguments or contrast-child ancestry."""
    task = str(node.get("description") or "").partition("(")[0].strip().rsplit(".", 1)[-1]
    return _TASK_FEATURES.get(task)


def cancellation_nodes(node):
    """Visit the same retained child tree used by RQ cancellation."""
    if not isinstance(node, dict):
        return
    yield node
    for children in node.get("children", {}).values():
        for child in children:
            yield from cancellation_nodes(child)
