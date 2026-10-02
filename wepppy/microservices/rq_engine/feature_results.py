"""FA-01 projection for existing open job polling; no admission-mode change."""
from pathlib import Path
from wepppy.weppcloud.utils.feature_access_data import protected_path, protected_source
from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
from wepppy.weppcloud.utils.feature_access_runtime import decide, resource_context
from .auth import AuthError
from .feature_access import verified_principal

_LIFECYCLE_FIELDS = frozenset({
    "job_id", "runid", "status", "started_at", "ended_at", "elapsed_s", "children",
    "culvert_batch_uuid", "progress", "queue", "queue_position", "queue_rank",
    "auth_actor", "created_at", "enqueued_at", "last_heartbeat", "origin",
    "queue_snapshot", "progress_updated_at", "stale", "is_stale",
})
_MIXED_RESULT_FIELDS = frozenset({"job_id", "job_ids", "runid", "status"})
_RESULT_KEYS = frozenset({"contrasts", "contrast_results", "path_ce", "selected_hillslopes",
                          "treatment_hillslopes", "sediment_reduction", "total_cost"})


def protected_job(node):
    description = str(node.get("description") or "")
    runid = str(node.get("runid") or "")
    return ("omni-contrast;;" in runid or "omni_contrast" in description
            or "path_cost_effective" in description or "path_ce_rq" in description)


def _protected_value(value):
    if isinstance(value, dict):
        return bool(_RESULT_KEYS.intersection(value)) or any(_protected_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_protected_value(item) for item in value)
    return isinstance(value, str) and protected_path(value)


def _protected_export_result(node):
    result = node.get("result")
    if not isinstance(result, dict) or not node.get("runid"):
        return False
    references = [result[key] for key in ("artifact_relpath", "manifest_relpath")
                  if isinstance(result.get(key), str)]
    if not references:
        return False
    from wepppy.weppcloud.utils.helpers import get_wd
    root = Path(get_wd(node["runid"]))
    return any(protected_source(root / path) for path in references)


def project_job_results(node, claims):
    """Project every child independently; entitled readers keep exact shapes."""
    entitlement = None

    def allowed():
        nonlocal entitlement
        if entitlement is None:
            try:
                principal = verified_principal(claims) if claims is not None else VerifiedPrincipal()
                entitlement = decide(principal, "omni_contrasts", "inspect", resource_context(protected_read=True)).allowed
            except AuthError:
                entitlement = False
        return entitlement

    def project(item):
        if not isinstance(item, dict):
            return item
        wholly_protected = protected_job(item) or _protected_export_result(item)
        mixed = _protected_value(item.get("result"))
        result = dict(item)
        if (wholly_protected or mixed) and not allowed():
            result = {key: value for key, value in item.items() if key in _LIFECYCLE_FIELDS}
            result["result"] = None
            if mixed and not wholly_protected and isinstance(item.get("result"), dict):
                result["result"] = {key: value for key, value in item["result"].items()
                                    if key in _MIXED_RESULT_FIELDS and not _protected_value(value)}
            result["description"] = "Restricted feature job"
            result["exc_info"] = None
        if isinstance(item.get("children"), dict):
            result["children"] = {key: [project(child) for child in children]
                                  for key, children in item["children"].items()}
            # RQ propagates a child's controlled error to its ordinary parent.
            # Do not re-expose it after redacting the originating child.
            if any(_redacted_descendant(child) for children in result["children"].values() for child in children):
                for key in ("error", "exc_info", "conditioning_diagnostics", "metadata"):
                    result.pop(key, None)
        return result

    return project(node)


def _redacted_descendant(node):
    if not isinstance(node, dict):
        return False
    return node.get("description") == "Restricted feature job" or any(
        _redacted_descendant(child) for children in node.get("children", {}).values() for child in children
    )
