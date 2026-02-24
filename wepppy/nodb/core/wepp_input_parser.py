from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wepppy.all_your_base import isfloat, isint

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
    return None


class WeppInputParser:
    def parse(self, wepp: "Wepp", kwds: dict[str, Any]) -> None:
        wepp.baseflow_opts.parse_inputs(kwds)
        wepp.phosphorus_opts.parse_inputs(kwds)
        if hasattr(wepp, "tcr_opts"):
            wepp.tcr_opts.parse_inputs(kwds)

        if hasattr(wepp, "snow_opts"):
            wepp.snow_opts.parse_inputs(kwds)

        if hasattr(wepp, "frost_opts"):
            wepp.frost_opts.parse_inputs(kwds)
        else:
            from wepppy.nodb.core.wepp import FrostOpts

            wepp.frost_opts = FrostOpts()

        wepp._guard_unitized_bounds()

        _channel_critical_shear = kwds.get("channel_critical_shear", None)
        if isfloat(_channel_critical_shear):
            wepp._channel_critical_shear = float(_channel_critical_shear)

        _channel_erodibility = kwds.get("channel_erodibility", None)
        if isfloat(_channel_erodibility):
            wepp._channel_erodibility = float(_channel_erodibility)

        _channel_manning_roughness_coefficient_bare = kwds.get(
            "channel_manning_roughness_coefficient_bare", None
        )
        if isfloat(_channel_manning_roughness_coefficient_bare):
            wepp._channel_manning_roughness_coefficient_bare = float(
                _channel_manning_roughness_coefficient_bare
            )

        _channel_manning_roughness_coefficient_veg = kwds.get(
            "channel_manning_roughness_coefficient_veg", None
        )
        if isfloat(_channel_manning_roughness_coefficient_veg):
            wepp._channel_manning_roughness_coefficient_veg = float(
                _channel_manning_roughness_coefficient_veg
            )

        _minimum_channel_width_m = kwds.get("minimum_channel_width_m", None)
        if isfloat(_minimum_channel_width_m):
            wepp._minimum_channel_width_m = float(_minimum_channel_width_m)

        _pmet_kcb = kwds.get("pmet_kcb", None)
        if isfloat(_pmet_kcb):
            wepp._pmet_kcb = float(_pmet_kcb)

        _pmet_rawp = kwds.get("pmet_rawp", None)
        if isfloat(_pmet_rawp):
            wepp._pmet_rawp = float(_pmet_rawp)

        _kslast = kwds.get("kslast", "")
        if isinstance(_kslast, (list, tuple, set)):
            _kslast = next((item for item in _kslast if item not in (None, "")), "")
        if isfloat(_kslast):
            wepp._kslast = float(_kslast)
        else:
            if _kslast in (None, ""):
                wepp._kslast = None
            elif isinstance(_kslast, str) and _kslast.strip().lower().startswith("none"):
                wepp._kslast = None

        _wepp_bin = kwds.get("wepp_bin", None)
        if _wepp_bin is not None:
            wepp._wepp_bin = _wepp_bin

        _dtchr_override = kwds.get("dtchr_override", None)
        if isfloat(_dtchr_override):
            _dtchr_override = int(_dtchr_override)
            if _dtchr_override < 60:
                raise ValueError("dtchr_override must be at least 60")
            wepp._dtchr_override = _dtchr_override

        _ichout_override = kwds.get("ichout_override", None)
        if _ichout_override is not None:
            if _ichout_override == "":
                wepp._ichout_override = None
            elif isint(_ichout_override):
                _ichout_value = int(_ichout_override)
                if _ichout_value not in (1, 3):
                    raise ValueError(
                        "ichout_override must be 1 (peak only) or 3 (full timestep hydrograph)"
                    )
                wepp._ichout_override = _ichout_value

        _chn_topaz_ids_of_interest = kwds.get("chn_topaz_ids_of_interest", None)
        if _chn_topaz_ids_of_interest is not None:
            values: list[int] = []
            if isinstance(_chn_topaz_ids_of_interest, (list, tuple, set)):
                for entry in _chn_topaz_ids_of_interest:
                    if entry in (None, ""):
                        continue
                    values.append(int(entry))
            else:
                tokens = str(_chn_topaz_ids_of_interest)
                if "," in tokens:
                    values = [int(v.strip()) for v in tokens.split(",") if v.strip()]
                elif " " in tokens:
                    values = [int(v.strip()) for v in tokens.split(" ") if v.strip()]
                else:
                    tokens = tokens.strip()
                    if tokens:
                        values = [int(tokens)]
            wepp._chn_topaz_ids_of_interest = values

        _delete_after_interchange = kwds.get("delete_after_interchange", None)
        if isinstance(_delete_after_interchange, (list, tuple, set)):
            _delete_after_interchange = next(
                (
                    item
                    for item in _delete_after_interchange
                    if item not in (None, "")
                ),
                None,
            )
        delete_after_interchange = _coerce_optional_bool(_delete_after_interchange)
        if delete_after_interchange is not None:
            # parse_inputs runs inside Wepp.parse_inputs() lock scope.
            # Setting the @nodb_setter property here would attempt to re-lock.
            wepp._delete_after_interchange = bool(delete_after_interchange)
