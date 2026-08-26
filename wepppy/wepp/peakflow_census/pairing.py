"""Faithful Phase 2A outer event pairing and screening flags."""

from __future__ import annotations

from typing import Any

import pandas as pd


def pair_events(baseline: pd.DataFrame, mutant: pd.DataFrame, trial: Any,
                *, peak_floor: float = 1e-7, runoff_floor: float = 1e-5,
                surplus_rate_floor: float = 1e-8) -> pd.DataFrame:
    keys = ["year", "day", "ofe", "ordinal"]
    columns = keys + ["runoff_post_m", "surdra_raw_m", "surdra_realized_m", "added_rate_m_s",
                      "forcing_mode", "solver", "peak_m_s"]
    paired = baseline[columns].merge(mutant[columns], on=keys, how="outer",
                                     suffixes=("_baseline", "_mutant"), indicator=True)
    for offset, (name, value) in enumerate((("trial_id", trial.trial_id), ("scenario", trial.scenario),
                                             ("hillslope_id", trial.hillslope_id), ("family", trial.family),
                                             ("direction", trial.direction))):
        paired.insert(offset, name, value)
    paired["baseline_event_present"] = paired._merge.isin(["both", "left_only"])
    paired["mutant_event_present"] = paired._merge.isin(["both", "right_only"])
    both = paired._merge == "both"
    peak_abs = (paired.peak_m_s_mutant - paired.peak_m_s_baseline).abs()
    peak_denominator = paired.peak_m_s_baseline.abs().clip(lower=peak_floor)
    peak_ratio = paired.peak_m_s_mutant / peak_denominator
    runoff_fraction = ((paired.runoff_post_m_mutant - paired.runoff_post_m_baseline).abs()
                       / paired.runoff_post_m_baseline.abs().clip(lower=runoff_floor))
    rate_max = pd.concat([paired.added_rate_m_s_baseline.abs(), paired.added_rate_m_s_mutant.abs()], axis=1).max(axis=1)
    rate_min = pd.concat([paired.added_rate_m_s_baseline.abs(), paired.added_rate_m_s_mutant.abs()], axis=1).min(axis=1)
    paired["event_presence_changed"] = ~both
    paired["solver_changed"] = both & (paired.solver_baseline != paired.solver_mutant)
    paired["forcing_mode_changed"] = both & (paired.forcing_mode_baseline != paired.forcing_mode_mutant)
    paired["surplus_depth_changed"] = both & ((paired.surdra_realized_m_mutant - paired.surdra_realized_m_baseline).abs() > runoff_floor)
    paired["peak_gt25pct_runoff_lt5pct"] = both & (peak_abs > peak_floor) & ((peak_abs / peak_denominator) > 0.25) & (runoff_fraction < 0.05)
    paired["peak_twofold"] = both & (peak_abs > peak_floor) & ((peak_ratio >= 2.0) | (peak_ratio <= 0.5))
    paired["surplus_rate_twofold"] = both & (rate_max > surplus_rate_floor) & ((rate_min <= surplus_rate_floor) | ((rate_max / rate_min.clip(lower=surplus_rate_floor)) > 2.0))
    signed_peak_change = paired.peak_m_s_mutant - paired.peak_m_s_baseline
    paired["expected_response_reversal"] = both & ((signed_peak_change > peak_floor) if trial.direction == "plus" else (signed_peak_change < -peak_floor))
    paired["candidate"] = paired[["event_presence_changed", "solver_changed", "peak_gt25pct_runoff_lt5pct",
                                  "peak_twofold", "surplus_rate_twofold", "expected_response_reversal"]].any(axis=1)
    return paired.drop(columns="_merge")
