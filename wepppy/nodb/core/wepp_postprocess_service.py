from __future__ import annotations

import json
from os.path import exists as _exists
from os.path import join as _join
from typing import TYPE_CHECKING, Any, Optional

from wepppy.all_your_base import NumpyEncoder, isinf, isnan
from wepppy.wepp.reports import ReturnPeriodDataset, ReturnPeriods

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


class WeppPostprocessService:
    def report_return_periods(
        self,
        wepp: "Wepp",
        rec_intervals: tuple[int, ...] = (50, 25, 20, 10, 5, 2),
        exclude_yr_indxs: Optional[list[int]] = None,
        method: str = "cta",
        gringorten_correction: bool = True,
        meoization: bool = True,
        exclude_months: Optional[list[int]] = None,
        chn_topaz_id_of_interest: Optional[int] = None,
        wait_for_inputs: bool = True,
    ) -> ReturnPeriods:
        output_dir = wepp.output_dir

        return_periods_fn = None
        cached_report: ReturnPeriods | None = None
        rep_yrs = None
        rep_mos = None
        if meoization:
            req_yrs = None if not exclude_yr_indxs else tuple(sorted({int(x) for x in exclude_yr_indxs}))
            req_mos = None if not exclude_months else tuple(sorted({int(x) for x in exclude_months}))

            parts = []
            if req_yrs:
                parts.append("exclude_yr_indxs=" + ",".join(map(str, req_yrs)))
            if req_mos:
                parts.append("exclude_months=" + ",".join(map(str, req_mos)))
            if gringorten_correction:
                parts.append("gringorten=True")
            if chn_topaz_id_of_interest is not None:
                parts.append("chn_topaz_id=" + str(chn_topaz_id_of_interest))
            suffix = ("__" + "__".join(parts)) if parts else ""
            return_periods_fn = _join(output_dir, f"return_periods{suffix}.json")

            if _exists(return_periods_fn):
                with open(return_periods_fn) as fp:
                    cached_report = ReturnPeriods.from_dict(json.load(fp))

                rep_yrs = getattr(cached_report, "exclude_yr_indxs", None)
                rep_mos = getattr(cached_report, "exclude_months", None)
                rep_yrs = None if not rep_yrs else tuple(sorted({int(x) for x in rep_yrs}))
                rep_mos = None if not rep_mos else tuple(sorted({int(x) for x in rep_mos}))

            if cached_report and req_yrs == rep_yrs and req_mos == rep_mos:
                has_calendar_year = any(
                    ("calendar_year" in row or "display_year" in row)
                    for measure_rows in cached_report.return_periods.values()
                    for row in measure_rows.values()
                )
                if has_calendar_year:
                    return cached_report
                cached_report = None

        readonly = _exists(_join(wepp.wd, "READONLY"))
        dataset = ReturnPeriodDataset(
            wepp.wd,
            auto_refresh=not readonly,
            wait_for_inputs=wait_for_inputs,
        )
        return_periods = dataset.create_report(
            rec_intervals,
            exclude_yr_indxs=exclude_yr_indxs,
            exclude_months=exclude_months,
            method=method,
            gringorten_correction=gringorten_correction,
            topaz_id=chn_topaz_id_of_interest,
        )

        if return_periods_fn is not None:
            with open(return_periods_fn, "w") as fp:
                json.dump(return_periods.to_dict(), fp, cls=NumpyEncoder)

        return return_periods

    def query_sub_val(
        self,
        wepp: "Wepp",
        measure: str,
    ) -> Optional[dict[str, dict[str, Any]]]:
        report = wepp.loss_report
        if report is None:
            return None

        translator = wepp.watershed_instance.translator_factory()

        def _resolve_identifier(row, *candidates):
            for key in candidates:
                if key not in row:
                    continue
                value = row.get(key)
                if value is None:
                    continue
                invalid = False
                try:
                    if value != value:
                        invalid = True
                except TypeError:
                    invalid = True
                if invalid:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    try:
                        return int(float(value))
                    except (TypeError, ValueError):
                        continue
            raise KeyError(f"Missing identifier columns {candidates} in loss hill record: {row}")

        d = {}
        for row in report.hill_tbl:
            wepp_id = _resolve_identifier(row, "wepp_id")
            topaz_id = translator.top(wepp=wepp_id)

            v = row.get(measure, None)
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(topaz_id=topaz_id, value=v)

        return d

    def query_chn_val(
        self,
        wepp: "Wepp",
        measure: str,
    ) -> Optional[dict[str, dict[str, Any]]]:
        from wepppy.wepp.interchange.watershed_loss import Loss

        translator = wepp.watershed_instance.translator_factory()
        output_dir = wepp.output_dir
        loss_pw0 = _join(output_dir, "loss_pw0.txt")

        if not _exists(loss_pw0):
            return None

        if not hasattr(wepp, "_loss_report"):
            wepp._loss_report = Loss(loss_pw0, wepp.has_phosphorus, wepp.wd)

        report = wepp._loss_report

        def _resolve_identifier(row, *candidates):
            for key in candidates:
                if key not in row:
                    continue
                value = row.get(key)
                if value is None:
                    continue
                invalid = False
                try:
                    if value != value:
                        invalid = True
                except TypeError:
                    invalid = True
                if invalid:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    try:
                        return int(float(value))
                    except (TypeError, ValueError):
                        continue
            raise KeyError(f"Missing identifier columns {candidates} in loss channel record: {row}")

        d = {}
        for row in report.chn_tbl:
            chn_enum = _resolve_identifier(row, "chn_enum")
            topaz_id = translator.top(chn_enum=chn_enum)

            v = row.get(measure, None)
            if isnan(v) or isinf(v):
                v = None

            d[str(topaz_id)] = dict(topaz_id=topaz_id, value=v)

        return d
