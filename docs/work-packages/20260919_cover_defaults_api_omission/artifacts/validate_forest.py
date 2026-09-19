"""Bounded fixture setup or readback on the disposable Forest validation fork."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import pandas as pd
from wepppy.nodb.core import Landuse, Wepp
from wepppy.wepp.management import Management
from wepppy.wepp.soils.utils import WeppSoilUtil

SOURCE = Path('/wc1/runs/eq/equestrian-bonheur')
TARGET = Path('/wc1/runs/co/cover-defaults-validation-20260919')
SOURCE_HASHES = {
    'landuse.nodb': '85b4069ecd303a580cdbd82fd49b8c27f82c503cb3dc834f3fe2177cf14ba16c',
    'wepp.nodb': '461e6dd846fd473d3dcda16c36747b1bb5eae7446e822476b4bf4730c9b29223',
    'soils.nodb': '6a55068083a1363a75f02e750a7f4f0ea6010385366da1783b9e6fa4d2e7d50e',
}
DEFAULTS = {'406': dict(cancov=0.75, inrcov=0.90, rilcov=0.90)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def management(path):
    return Management(Key='validation', ManagementFile=path.name,
                      ManagementDir=str(path.parent), Description='validation', Color=(0, 0, 0, 255))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--setup-defaults', action='store_true')
    parser.add_argument('--prepared', action='store_true')
    parser.add_argument('--outputs-after', type=float)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    for name, expected in SOURCE_HASHES.items():
        assert sha(SOURCE / name) == expected, name
    landuse = Landuse.getInstance(str(TARGET))
    wepp = Wepp.load_detached(str(TARGET))
    assert wepp.kslast == 0.0001 and wepp.wepp_bin == 'wepp_260803'
    if args.setup_defaults:
        # Explicit validation fixture, not a new user setting or source-project repair.
        assert landuse.cover_defaults_d is None
        with landuse.locked():
            landuse.cover_defaults_d = DEFAULTS
        print(json.dumps({'fixture': str(TARGET), 'defaults': DEFAULTS, 'kslast': wepp.kslast}))
        return
    landuse = Landuse.load_detached(str(TARGET))
    assert landuse.cover_defaults_d == DEFAULTS
    for field, value in DEFAULTS['406'].items():
        assert getattr(landuse.managements['406'], field + '_override') == value
    table = pd.read_parquet(TARGET / 'watershed/hillslopes.parquet')
    ids = {str(int(row.topaz_id)): int(row.wepp_id) for row in table.itertuples()}
    assert len(ids) == 455 and set(landuse.domlc_mofe_d) == set(ids)
    paths, segments = [], 0
    source_hashes = {}
    for topaz, mapping in landuse.domlc_mofe_d.items():
        assert set(mapping.values()) == {'406'}
        segments += len(mapping)
        soil_name = f'soils/hill_{topaz}.mofe.sol'
        assert sha(TARGET / soil_name) == sha(SOURCE / soil_name), soil_name
        paths.append(TARGET / soil_name)
        names = [f'landuse/hill_{topaz}.mofe.man']
        if args.prepared:
            names.append(f'wepp/runs/p{ids[topaz]}.man')
        for name in (f'landuse/hill_{topaz}.mofe.man', f'wepp/runs/p{ids[topaz]}.man'):
            source_hashes[name] = sha(SOURCE / name)
            source_man = management(SOURCE / name)
            assert all((i.data.cancov, i.data.inrcov, i.data.rilcov) == (.75, .85, .85)
                       for i in source_man.inis), name
        for name in names:
            actual = management(TARGET / name)
            assert len(actual.inis) == len(mapping), name
            assert all((i.data.cancov, i.data.inrcov, i.data.rilcov) == (.75, .9, .9)
                       for i in actual.inis), name
            paths.append(TARGET / name)
        if args.prepared:
            name = f'wepp/runs/p{ids[topaz]}.man'
            normalized = management(TARGET / name)
            normalized['ini.data.inrcov'] = 0.85
            normalized['ini.data.rilcov'] = 0.85
            assert str(normalized) == str(management(SOURCE / name)), name
            for ext in ('sol', 'slp', 'cli'):
                name = f'wepp/runs/p{ids[topaz]}.{ext}'
                if ext == 'sol':
                    original = WeppSoilUtil(str(SOURCE / name)).obj
                    actual = WeppSoilUtil(str(TARGET / name)).obj
                    original.pop('header', None)
                    actual.pop('header', None)
                    assert original == actual, name
                else:
                    assert sha(SOURCE / name) == sha(TARGET / name), name
                paths.append(TARGET / name)
    assert segments == 1065
    paths.extend(TARGET / name for name in ('landuse.nodb', 'wepp.nodb', 'soils.nodb', 'landuse.log', 'wepp.log'))
    output = None
    if args.outputs_after:
        path = TARGET / 'wepp/output/interchange/loss_pw0.hill.parquet'
        assert path.stat().st_mtime >= args.outputs_after
        frame = pd.read_parquet(path)
        assert len(frame) == 455 and frame.wepp_id.nunique() == 455
        assert set(map(int, frame.wepp_id)) == set(ids.values())
        assert frame[['Runoff Volume', 'Sediment Yield']].map(lambda x: float('-inf') < x < float('inf')).all().all()
        output = {'runoff_mm_year': frame['Runoff Volume'].sum() / frame['Hillslope Area'].sum() / 10,
                  'hillslope_sediment_t_year': frame['Sediment Yield'].sum() / 1000}
        paths.append(path)
    hashes = {str(path.relative_to(TARGET)): sha(path) for path in paths}
    if args.archive:
        assert args.archive.parent == TARGET / 'archives'
        with zipfile.ZipFile(args.archive) as archive:
            for name, expected in hashes.items():
                # Archive/restore append log messages; compare model records exactly.
                if name.endswith('.log'):
                    assert name in archive.namelist()
                else:
                    assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    print(json.dumps({'runid': TARGET.name, 'segments': segments, 'hillslopes': len(ids),
                      'source_unchanged': True, 'kslast': wepp.kslast, 'defaults': DEFAULTS,
                      'prepared': args.prepared, 'output': output, 'hashes': hashes,
                      'source_management_hashes': source_hashes}, sort_keys=True))


if __name__ == '__main__':
    main()
