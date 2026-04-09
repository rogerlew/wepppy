from __future__ import annotations

from typing import Any

from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.nodb.mods.swat import Swat


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
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    if value in (None, "", False):
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

    clip_soils = bool(_pop_scalar(controller_payload, "clip_soils", False))
    soils.clip_soils = clip_soils
    soils.rosetta_wc_fc_from_disturbed_bd_override = bool(
        _pop_scalar(controller_payload, "rosetta_wc_fc_from_disturbed_bd_override", False)
    )

    clip_soils_depth = _parse_int(_pop_scalar(controller_payload, "clip_soils_depth"))
    if clip_soils_depth is not None:
        soils.clip_soils_depth = clip_soils_depth

    clip_soils_minimum = bool(_pop_scalar(controller_payload, "clip_soils_minimum", False))
    soils.clip_soils_minimum = clip_soils_minimum

    clip_soils_minimum_depth = _parse_float(_pop_scalar(controller_payload, "clip_soils_minimum_depth"))
    if clip_soils_minimum_depth is not None:
        soils.clip_soils_minimum_depth = clip_soils_minimum_depth

    if clip_soils and clip_soils_minimum:
        max_depth = float(soils.clip_soils_depth)
        min_depth = float(soils.clip_soils_minimum_depth)
        if min_depth > max_depth:
            raise WeppRunPayloadValidationError(
                "Invalid soil depth clipping range",
                code="invalid_soil_depth_range",
                details=(
                    "clip_soils_minimum_depth must be less than or equal to "
                    "clip_soils_depth when both clipping options are enabled."
                ),
            )

    clip_hillslopes = bool(_pop_scalar(controller_payload, "clip_hillslopes", False))
    watershed.clip_hillslopes = clip_hillslopes

    # UI currently submits `hillslope_clip_length`; accept the historical
    # `clip_hillslope_length` key for backward compatibility.
    clip_hillslope_length_raw = _pop_scalar(controller_payload, "hillslope_clip_length", None)
    if clip_hillslope_length_raw is None:
        clip_hillslope_length_raw = _pop_scalar(controller_payload, "clip_hillslope_length", None)

    clip_hillslope_length = _parse_int(clip_hillslope_length_raw)
    if clip_hillslope_length is not None:
        watershed.clip_hillslope_length = clip_hillslope_length

    routine_overrides: dict[str, bool] = {}
    for payload_key, attr_name in _ROUTINE_CHECKBOX_ATTRS.items():
        if payload_key not in controller_payload:
            continue
        routine_state = _pop_scalar(controller_payload, payload_key, None)
        if isinstance(routine_state, bool):
            routine_overrides[attr_name] = bool(routine_state)

    initial_sat = _parse_float(_pop_scalar(controller_payload, "initial_sat"))
    if initial_sat is not None:
        soils.initial_sat = initial_sat

    reveg_scenario = _pop_scalar(controller_payload, "reveg_scenario", None)
    if isinstance(reveg_scenario, str):
        reveg_scenario = reveg_scenario.strip()
    if reveg_scenario is not None:
        from wepppy.nodb.mods.revegetation import Revegetation

        reveg = Revegetation.getInstance(wd)
        reveg.load_cover_transform(reveg_scenario)

    prep_details_on_run_completion = bool(
        _pop_scalar(controller_payload, "prep_details_on_run_completion", False)
    )
    arc_export_on_run_completion = bool(_pop_scalar(controller_payload, "arc_export_on_run_completion", False))
    legacy_arc_export_on_run_completion = bool(
        _pop_scalar(controller_payload, "legacy_arc_export_on_run_completion", False)
    )
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

    wepp.parse_inputs(controller_payload)
    _apply_swat_channel_params(
        wd,
        controller_payload,
        ron_cls=ron_cls,
        swat_cls=swat_cls,
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
