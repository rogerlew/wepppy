"""Read-only ground-cover acceptance; run with wctl run-python (no model edits)."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import pandas as pd
from wepppy.nodb.core import Landuse, Wepp
from wepppy.wepp.management import Management

SOURCE = Path('/wc1/runs/eq/equestrian-bonheur')
TARGET = Path('/wc1/runs/mo/mofe-ground-cover-validation-20260918')
SOURCE_NODB = {
    'landuse.nodb': '85b4069ecd303a580cdbd82fd49b8c27f82c503cb3dc834f3fe2177cf14ba16c',
    'wepp.nodb': '461e6dd846fd473d3dcda16c36747b1bb5eae7446e822476b4bf4730c9b29223',
    'soils.nodb': '6a55068083a1363a75f02e750a7f4f0ea6010385366da1783b9e6fa4d2e7d50e',
}


def read_management(path):
    return Management(Key='validation', ManagementFile=path.name,
                      ManagementDir=str(path.parent), Description='validation',
                      Color=(0, 0, 0, 255))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--prepared', action='store_true')
    parser.add_argument('--interrill', type=float, default=0.9)
    parser.add_argument('--rill', type=float, default=0.9)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    for name, expected in SOURCE_NODB.items():
        assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected, name
    landuse = Landuse.getInstance(str(TARGET))
    wepp = Wepp.getInstance(str(TARGET))
    assert wepp.wepp_bin == 'wepp_260803', wepp.wepp_bin
    assert landuse.cover_defaults_d is None
    table = pd.read_parquet(TARGET / 'watershed/hillslopes.parquet')
    ids = {str(int(row.topaz_id)): int(row.wepp_id) for row in table.itertuples()}
    assert set(map(str, landuse.domlc_mofe_d)) == set(ids)
    assert len(ids) == 455
    paths, segments = [], 0
    source_hashes = {}
    for topaz, mapping in landuse.domlc_mofe_d.items():
        assert set(mapping.values()) == {'406'}, (topaz, mapping)
        combined = TARGET / f'landuse/hill_{topaz}.mofe.man'
        check_paths = [combined]
        if args.prepared:
            check_paths.append(TARGET / f'wepp/runs/p{ids[str(topaz)]}.man')
        for path in check_paths:
            man = read_management(path)
            assert len(man.inis) == len(mapping), path
            for ini in man.inis:
                assert abs(ini.data.cancov - 0.75) < 1e-8, path
                assert abs(ini.data.inrcov - args.interrill) < 1e-8, path
                assert abs(ini.data.rilcov - args.rill) < 1e-8, path
            paths.append(path)
            source_path = SOURCE / path.relative_to(TARGET)
            source_hashes[str(path.relative_to(TARGET))] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            source_man = read_management(source_path)
            for ini in source_man.inis:
                assert (ini.data.cancov, ini.data.inrcov, ini.data.rilcov) == (0.75, 0.85, 0.85), source_path
        segments += len(mapping)
    assert segments == 1065
    hashes = {str(p.relative_to(TARGET)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if args.archive:
        assert args.archive.parent == TARGET / 'archives'
        with zipfile.ZipFile(args.archive) as archive:
            for name, expected in hashes.items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    print(json.dumps({'runid': TARGET.name, 'hillslopes': len(ids), 'segments': segments,
                      'checked_managements': len(paths), 'canopy': 0.75,
                      'interrill': args.interrill, 'rill': args.rill,
                      'wepp_binary': wepp.wepp_bin, 'source_nodb_unchanged': True,
                      'archive': str(args.archive) if args.archive else None,
                      'source_management_hashes': source_hashes,
                      'management_hashes': hashes}, sort_keys=True))


if __name__ == '__main__':
    main()
