"""Compare captured Omni outputs and persisted MOFE parameterization read-only."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path



ROOT = Path(__file__).parents[1]
RAW = ROOT / "artifacts" / "raw"
OUT = ROOT / "artifacts" / "omni_manual_comparison.csv"
SCENARIOS = ("uniform_low", "uniform_moderate", "uniform_high", "prescribed_fire", "thinning_40_75", "thinning_65_85")
METRICS = (
    "Avg. Ann. sediment discharge from outlet",
    "Avg. Ann. water discharge from outlet",
    "Avg. Ann. total hillslope soil loss",
    "Avg. Ann. total channel soil loss",
    "Sediment Delivery Ratio for Watershed",
)


def _state(path: Path) -> dict:
    value = json.loads(path.read_text())
    return value.get("py/state", value)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _counts(value) -> dict[str, int]:
    counts: dict[str, int] = {}

    def visit(item) -> None:
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
        else:
            counts[str(item)] = counts.get(str(item), 0) + 1

    visit(value)
    return counts


def main() -> None:
    with (RAW / "scenarios.out.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    metrics = {(row["scenario"], row["key"]): float(row["value"]) for row in rows}
    output = []
    for scenario in SCENARIOS:
        state = _state(RAW / f"{scenario}.landuse.nodb")
        managements = state.get("managements", {})
        dom_counts = _counts(state.get("domlc_d", {}))
        mofe_counts = _counts(state.get("domlc_mofe_d", {}))
        output.append({
            "scenario": scenario,
            "sediment_tonne_yr": metrics.get((scenario, METRICS[0])),
            "water_m3_yr": metrics.get((scenario, METRICS[1])),
            "hillslope_soil_loss_tonne_yr": metrics.get((scenario, METRICS[2])),
            "channel_soil_loss_tonne_yr": metrics.get((scenario, METRICS[3])),
            "sediment_delivery_ratio": metrics.get((scenario, METRICS[4])),
            "hillslopes": len(state.get("domlc_d", {})),
            "mofe_hillslopes": len(state.get("domlc_mofe_d", {})),
            "mofe_segments": sum(mofe_counts.values()),
            "dominant_management_counts": json.dumps(dom_counts, sort_keys=True),
            "management_parameters": json.dumps({
                key: {field: value.get(field) for field in ("desc", "disturbed_class", "cancov", "inrcov", "rilcov")}
                for key, value in managements.items()
                if str(key) in {"405", "406", "410", "418", "424", "426"}
            }, sort_keys=True),
            "landuse_nodb_sha256": _sha(RAW / f"{scenario}.landuse.nodb"),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output[0])
        writer.writeheader()
        writer.writerows(output)

    print(f"wrote {OUT}")
    for row in output:
        print(row["scenario"], row["sediment_tonne_yr"], row["water_m3_yr"], row["dominant_management_counts"])


if __name__ == "__main__":
    main()
