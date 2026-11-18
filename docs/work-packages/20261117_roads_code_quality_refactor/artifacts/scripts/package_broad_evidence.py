"""Retain exact broad-validation bytes; packaging makes no acceptance claim."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def package(spec_path, destination):
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    sources = [Path(name) for name in spec['files']]
    if not sources or any(not path.is_absolute() or not path.is_file() for path in sources):
        raise ValueError('Provide an explicit nonempty list of existing absolute source paths')
    if len(sources) != len(set(sources)) or len({path.name for path in sources}) != len(sources):
        raise ValueError('Evidence source paths and basenames must be unique')
    destination.mkdir(parents=True, exist_ok=False)
    receipt = {
        'status': 'incomplete', 'acceptance_claim': None,
        'purpose': spec.get('purpose', 'Exact evidence retention, including failures'),
        'spec_path': str(spec_path),
        'spec_sha256': hashlib.sha256(spec_bytes).hexdigest(),
        'packager_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python': sys.version, 'compression': 'gzip level 9, empty filename, mtime=0',
        'files': [],
    }
    receipt_path = destination / 'packaging_receipt.json'
    try:
        for source in sources:
            target = destination / (source.name + '.gz')
            source_hash = hashlib.sha256()
            original_size = 0
            with source.open('rb') as original, target.open('xb') as compressed:
                with gzip.GzipFile(filename='', mode='wb', compresslevel=9,
                                   fileobj=compressed, mtime=0) as archive:
                    for chunk in iter(lambda: original.read(1024 * 1024), b''):
                        source_hash.update(chunk)
                        original_size += len(chunk)
                        archive.write(chunk)
                compressed.flush()
                os.fsync(compressed.fileno())
            original_hash = source_hash.hexdigest()
            if sha256_file(source) != (original_hash, original_size):
                raise RuntimeError(f'Source changed during packaging: {source}')
            restored_hash = hashlib.sha256()
            restored_size = 0
            with gzip.open(target, 'rb') as restored:
                for chunk in iter(lambda: restored.read(1024 * 1024), b''):
                    restored_hash.update(chunk)
                    restored_size += len(chunk)
            if (restored_hash.hexdigest(), restored_size) != (original_hash, original_size):
                raise RuntimeError(f'Compressed roundtrip differs: {source}')
            compressed_hash, compressed_size = sha256_file(target)
            receipt['files'].append({
                'original_path': str(source), 'original_sha256': original_hash,
                'original_bytes': original_size, 'compressed_file': target.name,
                'compressed_sha256': compressed_hash, 'compressed_bytes': compressed_size,
                'decompression_verified': True,
            })
        # Recheck every original after all files have been packaged.
        for row in receipt['files']:
            if sha256_file(Path(row['original_path'])) != (row['original_sha256'], row['original_bytes']):
                raise RuntimeError(f"Source changed before receipt completion: {row['original_path']}")
        if spec_path.read_bytes() != spec_bytes:
            raise RuntimeError('Packaging specification changed during execution')
        receipt['status'] = 'complete'
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    result = package(args.spec, args.destination)
    print(json.dumps({'receipt': str(result), 'sha256': sha256_file(result)[0],
                      'acceptance_claim': None}))
