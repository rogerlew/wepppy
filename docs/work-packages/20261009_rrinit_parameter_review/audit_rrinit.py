#!/usr/bin/env python3
"""Read-only inventory and algebraic illustrations; does not execute WEPP."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

from wepppy.wepp.management import Management, get_management, load_map

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO/'wepppy/wepp/management/data'
BASE = {'forest', 'young forest', 'deciduous forest', 'mixed forest', 'shrub', 'tall grass'}


def relevant(name):
    return isinstance(name, str) and (name in BASE or ('fire' in name and any(name.startswith(x+' ') for x in ('forest', 'shrub', 'grass'))))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forest-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=HERE/'artifacts')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, files, roundtrips = [], {}, {}
    for path in sorted(DATA.glob('*.json')):
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict):
            continue
        selected = [k for k, v in raw.items() if isinstance(v, dict) and relevant(v.get('DisturbedClass', ''))]
        if not selected:
            continue
        mapping = load_map(str(path))
        files[str(path.relative_to(REPO))] = sha(path)
        for key in selected:
            row = mapping[key]
            management = get_management(key, _map=str(path))
            source = (Path(management.man_dir)/management.man_fn).resolve()
            source_name = str(source.relative_to(REPO))
            files[source_name] = sha(source)
            if source_name not in roundtrips:
                with tempfile.TemporaryDirectory(prefix='rrinit-readback-') as tmp:
                    target = Path(tmp)/'roundtrip.man'
                    target.write_text(str(management))
                    again = Management.load(None, target.name, tmp, None)
                    before = [(i.landuse, i.data.rrinit, i.data.rhinit) for i in management.inis]
                    after = [(i.landuse, i.data.rrinit, i.data.rhinit) for i in again.inis]
                    assert before == after, source_name
                    roundtrips[source_name] = True
            for n, ini in enumerate(management.inis, 1):
                d = ini.data
                rows.append(dict(mapping=path.name, key=key,
                    disturbed_class=row['DisturbedClass'], management=source_name,
                    initial_scenario=n, lanuse=ini.landuse, rrinit_m=d.rrinit,
                    rrinit_cm=100*d.rrinit, rhinit_m=d.rhinit, rfcum_mm=d.rfcum,
                    bdtill_g_cm3=d.bdtill, imngmt=d.imngmt, rtyp=d.rtyp,
                    rspace_m=d.rspace, width_m=d.width, inrcov=d.inrcov, rilcov=d.rilcov,
                    surface_sequences=len(management.surfs), operations=len(management.ops)))
    write_csv(args.output/'management-inventory.csv', rows)
    primary = [r for r in rows if r['mapping']=='disturbed.json']
    defaults = {}
    for r in primary:
        defaults.setdefault(r['disturbed_class'], set()).add(r['rrinit_m'])
    default_values = {k: sorted(v) for k,v in defaults.items()}
    extended = REPO/'wepppy/nodb/mods/disturbed/data/extended_land_soil_lookup.csv'
    files[str(extended.relative_to(REPO))] = sha(extended)
    discrepancies = []
    for row in csv.DictReader(extended.open()):
        cls = row['disturbed_class']
        if cls in defaults and float(row['ini.data.rrinit']) not in defaults[cls]:
            discrepancies.append(dict(disturbed_class=cls, texture=row['stext'],
                packaged_export_rrinit_m=float(row['ini.data.rrinit']),
                parsed_default_rrinit_m=default_values[cls]))
    variants = {}
    for row in rows:
        variants.setdefault(row['disturbed_class'], set()).add(row['rrinit_m'])
    base_lookup = REPO/'wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv'
    files[str(base_lookup.relative_to(REPO))] = sha(base_lookup)
    lookup = list(csv.DictReader(base_lookup.open()))
    ksflags = {c: sorted({r['ksflag'] for r in lookup if r['luse']==c}) for c in defaults}
    algebra = []
    for rr in (.006, .01, .02, .03, .04, .049, .05, .06, .08, .10):
        inrfo = math.exp(3.024-5.042*math.exp(-161*rr))
        for slope in (.05, .10, .20, .30, .40):
            algebra.append(dict(effective_rr_m=rr, slope_m_m=slope,
                potential_storage_mm=1000*max(0, .112*rr+3.1*rr*rr-1.2*rr*slope),
                zero_storage_slope_m_m=(.112+3.1*rr)/1.2,
                interrill_factor_rif=max(0, min(1, 1.14-23*rr)),
                roughness_critical_shear_multiplier=1+8*(rr-.006),
                initial_bare_interrill_friction=max(4.07, .5*inrfo**1.128)))
    write_csv(args.output/'static-equation-illustrations.csv', algebra)
    forest_files = {p.name: sha(p) for p in args.forest_source.glob('*.for')
                    if p.name in {'infile.for','soil.for','scon.for','irs.for','grna.for',
                                  'depsto.for','frcfac.for','rdat.for','infpar.for','param.for',
                                  'contin.for','tmpadj.for','melt.for','sndrft.for','mixpeak.for'}}
    summary = dict(scope='Static parsing and equation evaluation only; no model runs or default changes',
        wepppy_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        forest_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.forest_source,text=True).strip(),
        parsed_records=len(rows), maps=sorted({r['mapping'] for r in rows}),
        unique_managements=len(roundtrips), roundtrips=roundtrips,
        disturbed_defaults_m=default_values,
        values_across_all_maps_m={k:sorted(v) for k,v in variants.items()},
        packaged_export_discrepancies=discrepancies, current_ksflags=ksflags,
        inputs_sha256=files, forest_source_sha256=forest_files)
    (args.output/'inventory-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('inputs_sha256','forest_source_sha256','roundtrips')},indent=2))


if __name__=='__main__':
    main()
