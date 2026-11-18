"""Required installed-artifact readiness: real child and exact CSV byte readback."""
import asyncio
from pathlib import Path

from .runner import Converter


async def check():
    root = Path('/opt/parquet-csv')
    converter = Converter(Path('/usr/local/bin/parquet_csv_cli'), root / 'provenance.json',
                          Path('/tmp/wepppy-parquet-csv'))
    with await converter.convert(root / 'readiness.parquet') as artifact:
        if artifact.path.read_bytes() != (root / 'readiness.csv').read_bytes():
            raise RuntimeError('Native CSV readiness byte mismatch')
        if artifact.rows != 2:
            raise RuntimeError('Native CSV readiness row mismatch')
    print('parquet_csv_cli: ready (real conversion and CSV byte readback)')


if __name__ == '__main__':
    asyncio.run(check())
