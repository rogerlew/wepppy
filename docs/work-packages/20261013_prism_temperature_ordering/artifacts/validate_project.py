"""Real scratch-project PRISM build, reload, preparation and WEPP consumption."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

import numpy as np
import pandas as pd

from wepppy.climates.edde.cligen import read_cli
from wepppy.climates.edde.client import sha256, write_json
from wepppy.nodb.core import Climate, Watershed, Wepp
from wepppy.nodb.core.climate import ClimateMode, ClimateSpatialMode
import wepppyo3.climate.cli_revision_rust as native

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1] / '20261013_edde_v2_feasibility/artifacts'


def main():
    original = Path('/wc1/runs/cr/cryptic-beechnut')
    if len(sys.argv) == 3 and sys.argv[1] == '--consume':
        root = Path(sys.argv[2])
        source_hashes = json.loads((root / 'source-hashes.json').read_text())
        writers = json.loads((HERE / 'writer-validation.json').read_text())
        prior_root = Path(writers['root'])
    else:
        root = Path(tempfile.mkdtemp(prefix='prism-project-'))
        source_hashes = {}
        for source in original.glob('*.nodb'):
            source_hashes[source.name] = sha256(source)
            shutil.copy2(source, root / source.name)
        shutil.copytree(original / 'watershed', root / 'watershed')
        (root / 'climate').mkdir()
        # Actual retained future climate; state changes affect only this scratch copy.
        writers = json.loads((HERE / 'writer-validation.json').read_text())
        prior_root = Path(writers['root'])
        source = prior_root / 'workflows-full/WRF-MPI/SSP3-7.0/cryptic-beechnut/climate/wepp.cli'
        shutil.copy2(source, root / 'climate/wepp.cli')
        climate = Climate.getInstance(str(root))
        with climate.locked():
            climate._climate_mode = ClimateMode.ObservedPRISM
            climate._climate_spatialmode = ClimateSpatialMode.Multiple
            climate._observed_start_year = 2080
            climate._observed_end_year = 2099
            climate._input_years = 20
            climate.cli_fn = 'wepp.cli'
            climate.sub_cli_fns = None
            climate.sub_par_fns = None
        climate._prism_revision()
        (root / 'source-hashes.json').write_text(json.dumps(source_hashes))
        # Normal build and preparation jobs run in separate fresh processes.
        subprocess.run([sys.executable, __file__, '--consume', str(root)], check=True)
        return
    reloaded = Climate.getInstance(str(root))
    if not reloaded.sub_cli_fns: raise ValueError('No reloaded sub-climate mapping')
    watershed = Watershed.getInstance(str(root))
    translator = watershed.translator_factory()
    wepp = Wepp.getInstance(str(root))
    (root / 'wepp/runs').mkdir(parents=True, exist_ok=True)
    (root / 'wepp/output').mkdir(exist_ok=True)
    wepp._prep_climates(translator)
    sites = json.loads((STUDY.parent.parent / '20261008_dewpoint_openet/artifacts/manifest.json').read_text())['sites']
    site = next(s for s in sites if s['site'] == 'cryptic-beechnut-h132')
    prepared = root / 'wepp/runs' / f'p{site["hill"]}.cli'
    generated = root / 'climate' / reloaded.sub_cli_fns[str(site['topaz_id'])]
    if sha256(prepared) != sha256(generated): raise ValueError('Prepared climate differs')
    frame = read_cli(prepared)
    if not (frame.tmin <= frame.tmax).all(): raise ValueError('Prepared inversion')
    fixture = prior_root / 'fixtures' / site['site']
    for name, digest in site['source_hashes'].items():
        path = fixture / name
        if sha256(path) != digest: raise ValueError('Frozen fixture changed')
        if path.suffix != '.cli': shutil.copy2(path, root / 'wepp/runs' / name)
    control = root / 'wepp/runs' / f'p{site["hill"]}.run'
    lines = control.read_text().splitlines(); lines[-2] = '20'; control.write_text('\n'.join(lines) + '\n')
    binary = HERE.parents[3] / 'wepp_runner/bin/wepp_261010'
    with control.open('rb') as inp, (root/'wepp/stdout.log').open('wb') as out, (root/'wepp/stderr.log').open('wb') as err:
        result = subprocess.run([str(binary)], cwd=root/'wepp/runs', stdin=inp, stdout=out, stderr=err, timeout=180)
    if result.returncode or 'WEPP COMPLETED' not in (root/'wepp/stdout.log').read_text().upper():
        raise ValueError('WEPP did not complete')
    water = root / 'wepp/output' / f'H{site["hill"]}.wat.dat'
    rows = [list(map(float, fields)) for line in water.read_text().splitlines()
            if len(fields := line.split()) == 25 and fields[0].isdigit()]
    data = np.asarray(rows)
    dates = pd.DatetimeIndex(pd.to_datetime(data[:, 2].astype(int).astype(str)) + pd.to_timedelta(data[:, 1]-1, unit='D'))
    if len(data) != len(frame) or not np.isfinite(data).all() or not dates.equals(frame.index): raise ValueError('Invalid fresh WEPP output')
    np.testing.assert_allclose(data[:, 3], frame.prcp, rtol=0, atol=.011)
    for name, digest in source_hashes.items():
        if sha256(original/name) != digest: raise ValueError('Source project state changed')
    # Invoke the normal export entrypoint after spatialization, as climate orchestration does.
    reloaded._export_cli_parquet()
    summary = reloaded.sub_summary(str(site['topaz_id']))
    parquet = root / 'climate/wepp_cli.parquet'
    if not parquet.exists(): raise ValueError('Missing normal climate parquet export')
    table = pd.read_parquet(parquet)
    inventory = []
    for topaz_id, filename in reloaded.sub_cli_fns.items():
        revised = root / 'climate' / filename
        consumed = root / 'wepp/runs' / f'p{translator.wepp(top=int(topaz_id))}.cli'
        if sha256(revised) != sha256(consumed): raise ValueError('Prepared hillslope differs')
        daily = read_cli(revised)
        if not (daily.tmin <= daily.tmax).all(): raise ValueError('Project inversion')
        log = Path(str(revised) + '.temperature-ordering.log')
        if 'status=complete' not in log.read_text(): raise ValueError('Missing completed diagnostics')
        inventory.append(dict(topaz_id=topaz_id, generated=filename, sha256=sha256(revised), log_sha256=sha256(log)))
    evidence = HERE / 'project-consumer-evidence.tar.gz'
    retained = [prepared, generated, root/'climate/wepp.cli', parquet, water,
                *sorted((root/'wepp/runs').glob(f'p{site["hill"]}.*')),
                *sorted((root/'wepp').glob('*.log')),
                *sorted((root/'climate').glob('*.tif')),
                *sorted((root/'climate').glob('*.temperature-ordering.log'))]
    with tarfile.open(evidence, 'w:gz') as archive:
        for path in sorted(set(retained)):
            archive.add(path, arcname=str(path.relative_to(root)), recursive=False)
    write_json(HERE/'project-validation.json', dict(status='complete', root=str(root),
        archive=dict(path=evidence.name, sha256=sha256(evidence)), climate_inventory=inventory,
        original=str(original), source_nodb_sha256=source_hashes,
        uid=os.getuid(), gid=os.getgid(), groups=os.getgroups(),
        umask=next(l.split(':',1)[1].strip() for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('Umask:')),
        native_path=native.__file__, native_sha256=sha256(Path(native.__file__)),
        prepared=str(prepared.relative_to(root)), prepared_sha256=sha256(prepared),
        generated=str(generated.relative_to(root)), summary=summary,
        revised_hillslopes=len(reloaded.sub_cli_fns), parquet_rows=len(table), parquet_columns=list(table.columns),
        days=len(frame), water_sha256=sha256(water), binary_sha256=sha256(binary)))
    print('Actual project build/preparation/WEPP passed:', root)


if __name__ == '__main__': main()
