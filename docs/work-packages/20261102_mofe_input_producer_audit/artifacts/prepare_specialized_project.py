"""Construct a disposable configured acceptance case through owned APIs.

Compatibility plan: mutate only a supported fork; preserve source hashes and the
fork's original soil tree. Regenerate through Soils.build so 9005 reaches every
OFE. Synthetic RAP values exercise protocol, not a claim of observed site cover.
Complete Wepp.prep_hillslopes supplies all configured companion inputs.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import shutil
from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.io_wait import wait_for_paths
from wepppy.nodb.core import Ron, Landuse, Soils, Wepp, Watershed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.disturbed.disturbed import upgrade_disturbed_land_soil_lookup, write_disturbed_land_soil_lookup
from wepppy.nodb.mods.rap import RAP_TS
from wepppy.nodb.mods.revegetation import Revegetation
from wepppy.landcover.rap import RAP_Band
from wepppy.climates.cligen import ClimateFile
from wepppy.runtime_paths.mutations import mutate_root

SOURCE = Path('/wc1/runs/mi/mipa-awake-20261102')
DEST = Path('/wc1/runs/mi/mipa-rap-20261103')
EVIDENCE = Path('/wc1/holdouts/mipa-native-r7-20261103/configured-project')

def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}

def main():
    EVIDENCE.mkdir(exist_ok=True)
    if DEST.exists():
        raise FileExistsError(DEST)
    before = manifest(SOURCE)
    (EVIDENCE/'source-before.json').write_text(json.dumps(before, indent=2)+'\n')
    status=[]
    prepare_fork_run(SOURCE.name, DEST.name, undisturbify=False,
        skip_wepp_runs_output=True, skip_omni_scenarios_contrasts=True,
        status_channel='local-mipa', publish_status=lambda channel,message: status.append(message),
        get_wd=lambda runid: str(SOURCE), get_primary_wd=lambda runid: str(DEST),
        wait_for_paths=wait_for_paths, ron_cls=Ron, disturbed_cls=Disturbed,
        landuse_cls=Landuse, soils_cls=Soils, initialize_ttl=None)
    assert manifest(SOURCE)==before
    (EVIDENCE/'fork.json').write_text(json.dumps({'source':str(SOURCE),'destination':str(DEST),
        'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'status':status,'source_unchanged':True},indent=2)+'\n')
    shutil.copytree(DEST/'soils', EVIDENCE/'original-fork-soils')
    configure()

def configure():
    wd=str(DEST)
    w=Wepp.getInstance(wd)
    d=Disturbed.getInstance(wd)
    reference='/workdir/wepppy/wepppy/nodb/mods/revegetation/data/revegetation_land_soil_lookup.csv'
    shutil.copy2(d.lookup_fn,EVIDENCE/'original-lookup.csv')
    upgrade_disturbed_land_soil_lookup(d.lookup_fn,reference)
    with open(reference) as stream:
        canonical={(r['luse'],r['stext']):r for r in csv.DictReader(stream)}
    with open(d.lookup_fn) as stream:
        rows=list(csv.DictReader(stream))
    for row in rows:
        row.update(canonical.get((row['luse'],row['stext']),{}))
    write_disturbed_land_soil_lookup(d.lookup_fn,rows)
    d.sol_ver=9005
    d.fire_date='06 01 05'
    mutate_root(wd,'soils',lambda: Soils.getInstance(wd).build(max_workers=4,retrieve_gridded_ssurgo=False),purpose='mipa03-specialized-soils')
    rap=RAP_TS(wd,w._config)
    reveg=Revegetation(wd,w._config)
    reveg.load_cover_transform('20-yr_Recovery.csv')
    landuse=Landuse.getInstance(wd)
    years=sorted(set(ClimateFile(w.climate_instance.cli_path).years))
    bands=[RAP_Band.TREE,RAP_Band.SHRUB,RAP_Band.PERENNIAL_FORB_AND_GRASS,
           RAP_Band.ANNUAL_FORB_AND_GRASS,RAP_Band.LITTER,RAP_Band.BARE_GROUND]
    with rap.locked():
        rap.data={band:{str(year):{str(topaz):{str(ofe):base+int(ofe)*.1+(year-years[0])*.01
                    for ofe in mapping} for topaz,mapping in landuse.domlc_mofe_d.items()}
                    for year in years} for band,base in zip(bands,[15,8,6,4,25,10])}
        rap._rap_start_year=min(years)
        rap._rap_end_year=max(years)
    w.wepp_bin='wepp_261029'
    w.prep_hillslopes(max_workers=4)
    (EVIDENCE/'prepared-inputs.json').write_text(json.dumps(manifest(Path(w.runs_dir)),indent=2)+'\n')
    (EVIDENCE/'prepared.json').write_text(json.dumps({'years':years,'hills':len(landuse.domlc_mofe_d),
        'ofes':sum(len(v) for v in landuse.domlc_mofe_d.values()),'synthetic_cover':True,
        'transform':'20-yr_Recovery.csv','fire_date_saved':d.fire_date,
        'soil_versions':sorted(w.sol_versions),'binary_selection':w.wepp_bin},indent=2)+'\n')
    assert manifest(SOURCE)==json.loads((EVIDENCE/'source-before.json').read_text())
    print('COMPLETE configured specialized preparation',flush=True)

if __name__=='__main__':
    main()
