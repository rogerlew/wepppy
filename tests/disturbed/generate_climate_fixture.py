#!/usr/bin/env python3
"""Reproduce the canonical finite 100-year climate from committed station inputs."""
import hashlib
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

from wepppy.climates.cligen.binary_provenance import write_cligen_binary_identity

DATA = Path(__file__).parent/'data'


def validate_climate(path):
    rows=[line.split() for line in path.read_text().splitlines()[15:] if line.strip()]
    if not all(len(r)==13 and all(math.isfinite(float(v)) for v in r) for r in rows):
        raise ValueError(f'Nonfinite or malformed climate records: {path}')
    dates=[dt.date(int(r[2]),int(r[1]),int(r[0])) for r in rows]
    start,end=dt.date(2000,1,1),dt.date(2100,1,1)
    expected=[start+dt.timedelta(days=i) for i in range((end-start).days)]
    if dates != expected:
        raise ValueError(f'Climate must contain complete 2000-2099 forcing: {path}')
    return rows


def main():
    repo = Path(__file__).resolve().parents[2]
    binary = repo/'wepppy/climates/cligen/bin/cligen532'
    parameter = repo/'wepppy/climates/cligen/2015_par_files/or355362.par'
    with tempfile.TemporaryDirectory(prefix='disturbed-climate-') as tmp:
        shutil.copy2(parameter, Path(tmp)/parameter.name)
        command = [str(binary), '-ior355362.par', '-r26109', '-b2000', '-y100',
                   '-t5', '-omckenzie_2000_2099.cli']
        with (Path(tmp)/'cligen.log').open('w') as log:
            write_cligen_binary_identity(log, runner='disturbed_fixture', binary_path=str(binary))
            subprocess.run(command, input='n\n', text=True, cwd=tmp, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=30)
        p = Path(tmp)/'mckenzie_2000_2099.cli'
        rows = validate_climate(p)
        years = sorted({int(r[2]) for r in rows})
        assert years == list(range(2000,2100))
        target = DATA/p.name
        target.write_bytes(p.read_bytes())
        sha = lambda file: hashlib.sha256(Path(file).read_bytes()).hexdigest()
        provenance = dict(station='or355362', seed=26109, years=100,
            forcing='synthetic; no observed data or missing-value imputation',
            binary_sha256=sha(binary), parameter_sha256=sha(parameter),
            climate_sha256=sha(target), daily_records=len(rows), year_range=[years[0],years[-1]],
            annual_precipitation_mm=sum(float(r[3]) for r in rows)/100,
            command=command,
            reason='Historical test_climate.cli has only six years and 22 nonfinite dewpoints despite a 100-year header.')
        (DATA/'mckenzie_2000_2099.json').write_text(json.dumps(provenance,indent=2)+'\n')
        print(json.dumps(provenance,indent=2))


if __name__ == '__main__':
    main()
