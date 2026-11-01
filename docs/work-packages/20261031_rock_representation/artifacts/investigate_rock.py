"""Read-only dimensional and retained-capacity investigation; no model execution."""
import argparse
import csv
import hashlib
import json
import math
import runpy
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, default=Path.cwd())
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.repo = a.repo.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    helper = a.repo / "wepppy/wepp/soils/rock_fragments.py"
    conversions = runpy.run_path(str(helper))
    helper_before = sha(helper)
    grid = []
    for rho in [0.8, 1.0, 1.3, 1.6, 2.0]:
        for pct in range(101):
            v = pct / 100
            w = v * 2.65 / (v * 2.65 + (1-v) * rho)
            recovered = w * rho / (w * rho + (1-w) * 2.65)
            assert abs(recovered-v) < 1e-14
            assert abs(conversions["rock_volume_to_mass_fraction"](v, rho)-w) < 1e-14
            assert abs(conversions["rock_mass_to_volume_fraction"](w, rho)-v) < 1e-14
            emitted_w = float(f'{w * 100:.1f}') / 100
            native_w = min(emitted_w, .85)
            native_v = native_w * rho / (native_w*rho+(1-native_w)*2.65)
            old_v = v * rho / (v*rho+(1-v)*2.65)
            grid.append(dict(fine_density_g_cm3=rho, source_volume_fraction=v,
                             mass_fraction=w, roundtrip_volume=recovered,
                             old_direct_assignment_volume=old_v,
                             native_rounded_capped_volume=native_v,
                             native_cap_active=emitted_w>.85))
    overlap = []
    for b in [0, .1, .25, .5, .75, 1]:
        for s in [0, .1, .25, .5, .75, 1]:
            lo, hi = max(0, b+s-1), min(b, s)
            assert lo - 1e-15 <= b*s <= hi + 1e-15  # Binary rounding at decimal endpoints.
            overlap.append(dict(bare_fraction=b,total_rock_fraction=s,
                                exposed_lower=lo,exposed_upper=hi,
                                independence_exposed=b*s,
                                current_all_exposed_prior=hi))
    probe = a.repo/'out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe'
    records = sorted((probe/'cases').glob('*/*/*/result.json'))
    assert len(records) == 36
    bindings = {}
    def bind(path):
        st=path.stat();bindings[str(path)] = dict(sha256=sha(path),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
    layers=[]
    for p in records:
        bind(p); record=json.loads(p.read_text()); assert record['pass']
        trace=p.parent/'runs/storage-init.txt';bind(trace)
        assert sha(trace)==record['storage_init_sha256']
        seen=set()
        for line in trace.read_text().splitlines():
            cols=line.split()
            assert len(cols)==10
            if cols[0]!='SO_SCON_DRY': continue
            ofe,layer=map(int,cols[2:4]);assert (ofe,layer) not in seen;seen.add((ofe,layer))
            dry,fc,por,depth,fine,air=map(float,cols[4:]);assert all(math.isfinite(x) for x in [dry,fc,por,depth,fine,air])
            ceiling=por*fine
            layers.append(dict(history=record['case'],ofe=ofe,layer=layer,
                               dry_theta=dry,field_theta=fc,porosity=por,
                               fine_earth_fraction=fine,depth_m=depth,
                               candidate_effective_ceiling_theta=ceiling,
                               dry_margin_theta=ceiling-dry,
                               field_margin_theta=ceiling-fc,
                               retention_ordered=dry<=fc<=ceiling))
    assert len(layers)==586
    for name,saved in bindings.items():
        p=Path(name);st=p.stat()
        assert saved==dict(sha256=sha(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
    write_csv(a.out/'mass-volume-grid.csv',grid)
    write_csv(a.out/'surface-overlap-bounds.csv',overlap)
    write_csv(a.out/'capacity-ordering.csv',layers)
    assert sha(helper) == helper_before
    summary=dict(conversion_helper_sha256=helper_before,production_conversion_cells_verified=len(grid),status='PASS',mass_volume_cells=len(grid),overlap_cells=len(overlap),
                 retained_layers=len(layers),histories=36,
                 dry_exceeds_candidate_ceiling=sum(r['dry_margin_theta']<0 for r in layers),
                 field_exceeds_candidate_ceiling=sum(r['field_margin_theta']<0 for r in layers),
                 dry_exceeds_field=sum(r['dry_theta']>r['field_theta'] for r in layers),
                 minimum_dry_margin=min(r['dry_margin_theta'] for r in layers),
                 minimum_field_margin=min(r['field_margin_theta'] for r in layers),
                 native_cap_grid_cells=sum(r['native_cap_active'] for r in grid),
                 limitations='Read-only nonporous/static diagnostic; no capacity correction or field validation. Retention limits are observed after current guards, not recomputed.',
                 bindings=bindings,outputs={p.name:sha(p) for p in a.out.glob('*.csv')},reader_sha256=sha(Path(__file__)))
    (a.out/'receipt.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['bindings','outputs']},indent=2))


if __name__=='__main__': main()
