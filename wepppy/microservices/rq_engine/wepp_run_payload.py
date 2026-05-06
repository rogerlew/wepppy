from __future__ import annotations

import logging
from typing import Any

from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.swat import Swat

logger = logging.getLogger(__name__)


class WeppRunPayloadValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


_ROUTINE_CHECKBOX_ATTRS: dict[str, str] = {
    "checkbox_hourly_seepage": "_run_wepp_ui",
    "checkbox_wepp_watershed": "_run_wepp_watershed",
    "checkbox_wepp_pmet": "_run_pmet",
    "checkbox_wepp_frost": "_run_frost",
    "checkbox_wepp_tcr": "_run_tcr",
    "checkbox_wepp_snow": "_run_snow",
}

WEPP_DSS_EXCLUDE_ORDER_FIELDS: set[str] = {f"dss_export_exclude_order_{i}" for i in range(1, 6)}

WEPP_BOOLEAN_FIELDS: set[str] = {
    "clip_soils",
    "clip_soils_minimum",
    "rosetta_wc_fc_from_disturbed_bd_override",
    "clip_hillslopes",
    "prep_details_on_run_completion",
    "arc_export_on_run_completion",
    "legacy_arc_export_on_run_completion",
    "dss_export_on_run_completion",
    *_ROUTINE_CHECKBOX_ATTRS.keys(),
    *WEPP_DSS_EXCLUDE_ORDER_FIELDS,
}

SUPPORTED_WEPP_RUN_FORM_FIELDS: set[str] = {
    # Channel + routing parameters
    "channel_critical_shear",
    "channel_erodibility",
    "minimum_channel_width_m",
    "channel_manning_roughness_coefficient_bare",
    "channel_manning_roughness_coefficient_veg",
    "tcr_opts_taumin",
    "tcr_opts_taumax",
    "tcr_opts_kch",
    "tcr_opts_nch",
    # PMET / snow / frost / baseflow options
    "pmet_kcb",
    "pmet_rawp",
    "snow_opts_rst",
    "snow_opts_newsnw",
    "snow_opts_ssd",
    "frost_opts_wintRed",
    "frost_opts_fineTop",
    "frost_opts_fineBot",
    "frost_opts_ksnowf",
    "frost_opts_kresf",
    "frost_opts_ksoilf",
    "frost_opts_kfactor1",
    "frost_opts_kfactor2",
    "frost_opts_kfactor3",
    "baseflow_opts_gwstorage",
    "baseflow_opts_bfcoeff",
    "baseflow_opts_dscoeff",
    "baseflow_opts_bfthreshold",
    # Soil/hillslope/lookup modifiers
    "clip_soils",
    "clip_soils_depth",
    "clip_soils_minimum",
    "clip_soils_minimum_depth",
    "rosetta_wc_fc_from_disturbed_bd_override",
    "initial_sat",
    "clip_hillslopes",
    "hillslope_clip_length",
    "clip_hillslope_length",
    # WEPP runtime and export controls
    "wepp_bin",
    "pass_family",
    "kslast",
    "dtchr_override",
    "ichout_override",
    "chn_topaz_ids_of_interest",
    "delete_after_interchange",
    "prep_details_on_run_completion",
    "arc_export_on_run_completion",
    "legacy_arc_export_on_run_completion",
    "dss_export_on_run_completion",
    *WEPP_DSS_EXCLUDE_ORDER_FIELDS,
    # Routines + ancillary options
    "checkbox_wepp_tcr",
    "checkbox_wepp_pmet",
    "checkbox_wepp_frost",
    "checkbox_wepp_snow",
    "checkbox_wepp_watershed",
    "checkbox_hourly_seepage",
    "reveg_scenario",
    "surf_runoff",
    "lateral_flow",
    "baseflow",
    "sediment",
}


def _pop_scalar(mapping: dict[str, Any], key: str, default: Any = None) -> Any:
    if key not in mapping:
        return default
    value = mapping.pop(key)
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if item not in (None, ""):
                return item
        return default
    return value


def _parse_int(value: Any) -> int | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_swat_channel_params(
    wd: str,
    payload: dict[str, Any],
    *,
    ron_cls=Ron,
    swat_cls=Swat,
) -> None:
    ron = ron_cls.getInstance(wd)
    mods = ron.mods or []
    if "swat" not in mods:
        return
    swat = swat_cls.getInstance(wd)
    swat.parse_inputs(payload)


def _controller_lock_order_key(controller: Any) -> tuple[str, str]:
    """Provide deterministic cross-controller lock ordering."""

    class_name = str(getattr(controller, "class_name", type(controller).__name__))
    return (class_name, type(controller).__name__)


def _finalize_grouped_wepp_run_payload_controller(controller: Any) -> None:
    """Persist grouped WEPP payload updates for a locked controller."""

    finalize_hook = getattr(controller, "finalize_grouped_wepp_run_payload_updates", None)
    if callable(finalize_hook):
        finalize_hook()
        return
    controller.dump()


def _post_finalize_grouped_wepp_run_payload_controller(
    *,
    label: str,
    controller: Any,
) -> None:
    """Run post-dump semantics for grouped WEPP payload updates."""

    post_finalize_hook = getattr(controller, "post_finalize_grouped_wepp_run_payload_updates", None)
    if not callable(post_finalize_hook):
        return
    try:
        post_finalize_hook()
    except Exception:
        logger.exception(
            "WEPP grouped payload post-dump failed for %s controller",
            label,
        )
        raise


def _resolve_grouped_update_lock_order(
    *,
    soils: Any,
    include_soils: bool,
    watershed: Any,
    include_watershed: bool,
) -> list[tuple[str, Any]]:
    lock_targets: list[tuple[str, Any]] = []
    if include_soils:
        lock_targets.append(("soils", soils))
    if include_watershed:
        lock_targets.append(("watershed", watershed))
    return sorted(lock_targets, key=lambda item: _controller_lock_order_key(item[1]))


def _acquire_grouped_update_locks(
    *,
    lock_order: list[tuple[str, Any]],
) -> list[tuple[str, Any]]:
    """Acquire grouped-update locks in deterministic order."""

    if not lock_order:
        return []
    locked_controllers: list[tuple[str, Any]] = []

    try:
        for label, controller in lock_order:
            controller.lock()
            locked_controllers.append((label, controller))
    except Exception:
        for label, controller in reversed(locked_controllers):
            try:
                controller.unlock()
            except Exception:
                logger.exception(
                    "WEPP grouped payload unlock failed for %s controller",
                    label,
                )
        raise

    return locked_controllers


def _apply_grouped_soils_watershed_updates(
    *,
    soils: Any,
    watershed: Any,
    clip_soils: bool | None,
    clip_soils_depth: int | None,
    clip_soils_minimum: bool | None,
    clip_soils_minimum_depth: float | None,
    rosetta_wc_fc_from_disturbed_bd_override: bool | None,
    initial_sat: float | None,
    clip_hillslopes: bool | None,
    clip_hillslope_length: int | None,
    lock_order: list[tuple[str, Any]] | None = None,
    locks_already_held: bool = False,
) -> None:
    """Apply grouped Soils+Watershed updates with bounded rollback guarantees."""

    has_soils_updates = any(
        value is not None
        for value in (
            clip_soils,
            clip_soils_depth,
            clip_soils_minimum,
            clip_soils_minimum_depth,
            rosetta_wc_fc_from_disturbed_bd_override,
            initial_sat,
        )
    )
    has_watershed_updates = any(
        value is not None
        for value in (
            clip_hillslopes,
            clip_hillslope_length,
        )
    )
    if lock_order is None:
        lock_order = _resolve_grouped_update_lock_order(
            soils=soils,
            include_soils=has_soils_updates,
            watershed=watershed,
            include_watershed=has_watershed_updates,
        )
    if not lock_order:
        return

    locked_controllers: list[tuple[str, Any]] = []
    committed_controllers: list[tuple[str, Any]] = []
    snapshots_by_label: dict[str, dict[str, Any]] = {}
    staged_by_label: dict[str, bool] = {}
    primary_exception: BaseException | None = None
    unlock_failure: BaseException | None = None

    try:
        if locks_already_held:
            locked_controllers.extend(lock_order)
        else:
            for label, controller in lock_order:
                controller.lock()
                locked_controllers.append((label, controller))

        for label, controller in lock_order:
            snapshots_by_label[label] = controller.snapshot_wepp_run_payload_updates()

        if has_soils_updates:
            staged_by_label["soils"] = soils.stage_wepp_run_payload_updates(
                clip_soils=clip_soils,
                clip_soils_depth=clip_soils_depth,
                clip_soils_minimum=clip_soils_minimum,
                clip_soils_minimum_depth=clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override=rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat=initial_sat,
            )
        if has_watershed_updates:
            staged_by_label["watershed"] = watershed.stage_wepp_run_payload_updates(
                clip_hillslopes=clip_hillslopes,
                clip_hillslope_length=clip_hillslope_length,
            )

        for label, controller in lock_order:
            should_commit = staged_by_label.get(label, False)
            if not should_commit:
                continue
            committed_controllers.append((label, controller))
            _finalize_grouped_wepp_run_payload_controller(controller)
    except Exception as exc:
        primary_exception = exc
        for label, controller in lock_order:
            snapshot = snapshots_by_label.get(label)
            if snapshot is None:
                continue
            try:
                controller.restore_wepp_run_payload_updates(snapshot)
            except Exception:
                logger.exception(
                    "WEPP grouped payload restore failed for %s controller",
                    label,
                )

        for label, controller in reversed(committed_controllers):
            try:
                _finalize_grouped_wepp_run_payload_controller(controller)
            except Exception:
                # Rollback boundary: keep original failure and emit context.
                logger.exception(
                    "WEPP grouped payload rollback failed for %s controller",
                    label,
                )
        raise
    finally:
        for label, controller in reversed(locked_controllers):
            try:
                controller.unlock()
            except Exception as exc:
                # Unlock boundary: preserve prior failures, but surface success-path unlock errors.
                logger.exception(
                    "WEPP grouped payload unlock failed for %s controller",
                    label,
                )
                if primary_exception is None and unlock_failure is None:
                    unlock_failure = exc

    if primary_exception is None and unlock_failure is not None:
        raise unlock_failure

    for label, controller in committed_controllers:
        _post_finalize_grouped_wepp_run_payload_controller(
            label=label,
            controller=controller,
        )


def apply_wepp_run_payload(
    wd: str,
    payload: dict[str, Any],
    *,
    wepp_cls=Wepp,
    soils_cls=Soils,
    watershed_cls=Watershed,
    ron_cls=Ron,
    swat_cls=Swat,
) -> Wepp:
    controller_payload: dict[str, Any] = dict(payload)
    wepp = wepp_cls.getInstance(wd)
    soils = soils_cls.getInstance(wd)
    watershed = watershed_cls.getInstance(wd)

    clip_soils_update: bool | None = None
    clip_soils_depth_update: int | None = None
    clip_soils_minimum_update: bool | None = None
    clip_soils_minimum_depth_update: float | None = None
    rosetta_wc_fc_from_disturbed_bd_override_update: bool | None = None
    initial_sat_update: float | None = None
    clip_hillslopes_update: bool | None = None
    clip_hillslope_length_update: int | None = None

    clip_soils = bool(getattr(soils, "clip_soils", False))
    if "clip_soils" in controller_payload:
        clip_soils = bool(_pop_scalar(controller_payload, "clip_soils", False))
        clip_soils_update = clip_soils
    if "rosetta_wc_fc_from_disturbed_bd_override" in controller_payload:
        rosetta_wc_fc_from_disturbed_bd_override_update = bool(
            _pop_scalar(controller_payload, "rosetta_wc_fc_from_disturbed_bd_override", False)
        )

    clip_soils_depth = _parse_int(_pop_scalar(controller_payload, "clip_soils_depth"))
    if clip_soils_depth is not None:
        clip_soils_depth_update = clip_soils_depth

    clip_soils_minimum = bool(getattr(soils, "clip_soils_minimum", False))
    if "clip_soils_minimum" in controller_payload:
        clip_soils_minimum = bool(_pop_scalar(controller_payload, "clip_soils_minimum", False))
        clip_soils_minimum_update = clip_soils_minimum

    clip_soils_minimum_depth = _parse_float(_pop_scalar(controller_payload, "clip_soils_minimum_depth"))
    if clip_soils_minimum_depth is not None:
        clip_soils_minimum_depth_update = clip_soils_minimum_depth

    if clip_soils and clip_soils_minimum:
        max_depth = float(
            clip_soils_depth_update
            if clip_soils_depth_update is not None
            else soils.clip_soils_depth
        )
        min_depth = float(
            clip_soils_minimum_depth_update
            if clip_soils_minimum_depth_update is not None
            else soils.clip_soils_minimum_depth
        )
        if min_depth > max_depth:
            raise WeppRunPayloadValidationError(
                "Invalid soil depth clipping range",
                code="invalid_soil_depth_range",
                details=(
                    "clip_soils_minimum_depth must be less than or equal to "
                    "clip_soils_depth when both clipping options are enabled."
                ),
            )

    if "clip_hillslopes" in controller_payload:
        clip_hillslopes_update = bool(_pop_scalar(controller_payload, "clip_hillslopes", False))

    # UI currently submits `hillslope_clip_length`; accept the historical
    # `clip_hillslope_length` key for backward compatibility.
    clip_hillslope_length_raw = _pop_scalar(controller_payload, "hillslope_clip_length", None)
    if clip_hillslope_length_raw is None:
        clip_hillslope_length_raw = _pop_scalar(controller_payload, "clip_hillslope_length", None)

    clip_hillslope_length = _parse_int(clip_hillslope_length_raw)
    if clip_hillslope_length is not None:
        clip_hillslope_length_update = clip_hillslope_length

    initial_sat = _parse_float(_pop_scalar(controller_payload, "initial_sat"))
    if initial_sat is not None:
        initial_sat_update = initial_sat

    has_soils_grouped_updates = any(
        value is not None
        for value in (
            clip_soils_update,
            clip_soils_depth_update,
            clip_soils_minimum_update,
            clip_soils_minimum_depth_update,
            rosetta_wc_fc_from_disturbed_bd_override_update,
            initial_sat_update,
        )
    )
    has_watershed_grouped_updates = any(
        value is not None
        for value in (
            clip_hillslopes_update,
            clip_hillslope_length_update,
        )
    )
    grouped_lock_order: list[tuple[str, Any]] = []
    if has_soils_grouped_updates or has_watershed_grouped_updates:
        grouped_lock_order = _resolve_grouped_update_lock_order(
            soils=soils,
            include_soils=has_soils_grouped_updates,
            watershed=watershed,
            include_watershed=has_watershed_grouped_updates,
        )

    routine_overrides: dict[str, bool] = {}
    for payload_key, attr_name in _ROUTINE_CHECKBOX_ATTRS.items():
        if payload_key not in controller_payload:
            continue
        routine_state = _pop_scalar(controller_payload, payload_key, None)
        if isinstance(routine_state, bool):
            routine_overrides[attr_name] = bool(routine_state)

    reveg_scenario = _pop_scalar(controller_payload, "reveg_scenario", None)
    if isinstance(reveg_scenario, str):
        reveg_scenario = reveg_scenario.strip()

    prep_details_on_run_completion = bool(
        getattr(
            wepp,
            "prep_details_on_run_completion",
            getattr(wepp, "_prep_details_on_run_completion", False),
        )
    )
    if "prep_details_on_run_completion" in controller_payload:
        prep_details_on_run_completion = bool(
            _pop_scalar(controller_payload, "prep_details_on_run_completion", False)
        )
    arc_export_on_run_completion = bool(
        getattr(
            wepp,
            "arc_export_on_run_completion",
            getattr(wepp, "_arc_export_on_run_completion", False),
        )
    )
    if "arc_export_on_run_completion" in controller_payload:
        arc_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "arc_export_on_run_completion", False)
        )
    legacy_arc_export_on_run_completion = bool(
        getattr(
            wepp,
            "legacy_arc_export_on_run_completion",
            getattr(wepp, "_legacy_arc_export_on_run_completion", False),
        )
    )
    if "legacy_arc_export_on_run_completion" in controller_payload:
        legacy_arc_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "legacy_arc_export_on_run_completion", False)
        )
    dss_export_on_run_completion = bool(
        getattr(
            wepp,
            "dss_export_on_run_completion",
            getattr(wepp, "_dss_export_on_run_completion", False),
        )
    )
    if "dss_export_on_run_completion" in controller_payload:
        dss_export_on_run_completion = bool(
            _pop_scalar(controller_payload, "dss_export_on_run_completion", False)
        )

    dss_export_exclude_orders: list[int] = []
    exclude_orders_supplied = False
    for i in range(1, 6):
        key = f"dss_export_exclude_order_{i}"
        if key not in controller_payload:
            continue
        exclude_orders_supplied = True
        if bool(_pop_scalar(controller_payload, key, False)):
            dss_export_exclude_orders.append(i)
    if not exclude_orders_supplied:
        dss_export_exclude_orders = wepp.dss_excluded_channel_orders

    grouped_locked_controllers = _acquire_grouped_update_locks(lock_order=grouped_lock_order)
    grouped_locks_transferred = False
    try:
        wepp.parse_inputs(controller_payload)
        _apply_swat_channel_params(
            wd,
            controller_payload,
            ron_cls=ron_cls,
            swat_cls=swat_cls,
        )
        if reveg_scenario is not None:
            from wepppy.nodb.mods.revegetation import Revegetation

            reveg = Revegetation.getInstance(wd)
            reveg.load_cover_transform(reveg_scenario)

        if has_soils_grouped_updates or has_watershed_grouped_updates:
            grouped_locks_transferred = bool(grouped_locked_controllers)
            _apply_grouped_soils_watershed_updates(
                soils=soils,
                watershed=watershed,
                clip_soils=clip_soils_update,
                clip_soils_depth=clip_soils_depth_update,
                clip_soils_minimum=clip_soils_minimum_update,
                clip_soils_minimum_depth=clip_soils_minimum_depth_update,
                rosetta_wc_fc_from_disturbed_bd_override=rosetta_wc_fc_from_disturbed_bd_override_update,
                initial_sat=initial_sat_update,
                clip_hillslopes=clip_hillslopes_update,
                clip_hillslope_length=clip_hillslope_length_update,
                lock_order=grouped_lock_order if grouped_locks_transferred else None,
                locks_already_held=grouped_locks_transferred,
            )
    finally:
        if grouped_locked_controllers and not grouped_locks_transferred:
            for label, controller in reversed(grouped_locked_controllers):
                try:
                    controller.unlock()
                except Exception:
                    logger.exception(
                        "WEPP grouped payload unlock failed for %s controller",
                        label,
                    )

    with wepp.locked():
        for attr_name, routine_state in routine_overrides.items():
            setattr(wepp, attr_name, bool(routine_state))
        wepp._prep_details_on_run_completion = prep_details_on_run_completion
        wepp._arc_export_on_run_completion = arc_export_on_run_completion
        wepp._legacy_arc_export_on_run_completion = legacy_arc_export_on_run_completion
        wepp._dss_export_on_run_completion = dss_export_on_run_completion
        wepp._dss_excluded_channel_orders = dss_export_exclude_orders

    return wepp


__all__ = [
    "SUPPORTED_WEPP_RUN_FORM_FIELDS",
    "WEPP_BOOLEAN_FIELDS",
    "WEPP_DSS_EXCLUDE_ORDER_FIELDS",
    "WeppRunPayloadValidationError",
    "apply_wepp_run_payload",
]
