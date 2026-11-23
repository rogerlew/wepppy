from __future__ import annotations

import json
from pathlib import Path

import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.roads import Roads


@pytest.fixture
def modeled_accounting_stub(monkeypatch):
    """Isolate accounting in routing tests whose PASS files are text sentinels."""
    from wepppy.wepp.interchange import roads_accounting

    def prepare(self, canonical_ids, records):
        targets = []
        for target in canonical_ids:
            rows = [r for r in records if r.get("status") == "completed"
                    and r["target_hillslope_wepp_id"] == target]
            replacement = [r for r in rows if r.get("routing_mode") == "outslope_unrutted_replacement"]
            active = replacement or rows
            output = Path(self.roads_output_dir) / f"H{target}.pass.dat"
            baseline = Path(self.wepp_instance.output_dir) / f"H{target}.pass.dat"
            paths = [str(Path(self.wd) / r["segment_pass_relpath"]) for r in active]
            if replacement and len(paths) == 1:
                self._safe_link_or_copy(paths[0], str(output))
            elif active:
                self._combine_target_hillslope_pass(
                    base_pass_path=paths[0] if replacement else str(baseline),
                    road_pass_paths=paths[1:] if replacement else paths,
                    output_pass_path=str(output),
                    **({"strategy": "phase4"} if replacement else {}),
                )
            else:
                self._safe_link_or_copy(str(baseline), str(output))
            targets.append({"id": target, "mode": "replacement" if replacement else "additive" if rows else "unchanged"})
        return {"targets": targets}

    monkeypatch.setattr(Roads, "_prepare_modeled_area_accounting", prepare)
    monkeypatch.setattr(roads_accounting, "mark_routed", lambda root: None)

    # Routing tests below deliberately replace native soil/PASS producers with
    # text sentinels. Keep their new provenance boundary explicit; dedicated
    # parameterization tests exercise real writer/readback validation.
    def attach_parameterization(self, records):
        signature = roads_module.roads_parameterization.configuration_hash(self._parameterization)
        for record in records:
            record["parameterization"] = {"configuration_hash": signature, "ofes": []}

    def comparison_snapshot(wd, **kwargs):
        result = {"available": False, "reason": "Routing-test native producers are stubbed."}
        target = Path(wd) / "wepp/roads/output/roads.parameterization.comparison.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result))
        return result

    monkeypatch.setattr(Roads, "_attach_parameterization_records", attach_parameterization)
    monkeypatch.setattr(roads_module._parameterization_comparisons, "write_comparison_snapshot", comparison_snapshot)
