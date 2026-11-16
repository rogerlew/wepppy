"""Uncached SDA admission probe; run under the batch-worker identity."""
import argparse
import datetime
import json
import tempfile
from pathlib import Path

from wepppy.soils.ssurgo import SurgoSoilCollection
from wepppy.wepp.single_input import validate_soil_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mukey', required=True, type=int)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='santee-sda-') as directory:
        collection = SurgoSoilCollection([args.mukey], cache_db_path=directory + '/cache.sqlite')
        counts = dict(collection._cache_table_counts())
        assert counts['component'] > 0 and counts['chorizon'] > 0, counts
        collection.makeWeppSoils(max_workers=1)
        assert args.mukey in collection.getValidWeppSoils()
        collection.writeWeppSoils(directory)
        soil = Path(directory, str(args.mukey) + '.sol').read_text()
        validate_soil_text(soil, max_ofes=32)
        print(json.dumps({'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          'mukey': args.mukey, 'tables': counts, 'soil_valid': True,
                          'cache': 'new temporary SQLite', 'endpoint': 'NRCS SDA Tabular API'}))


if __name__ == '__main__':
    main()
