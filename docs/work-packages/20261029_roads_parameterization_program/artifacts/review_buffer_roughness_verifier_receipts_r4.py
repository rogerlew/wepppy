"""Read-only exact validation of retained copied-audit and nonmutation receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import pyarrow.parquet as pq


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    gate = read(args.gate)
    assert gate['passed']
    bindings = {str(args.gate.resolve()): sha(args.gate), str(Path(__file__).resolve()): sha(__file__)}
    bindings.update(gate['verification_receipts'])
    cases, table_checks, serialized_differences = set(), 0, 0
    for name, digest in gate['verification_receipts'].items():
        path = Path(name)
        assert sha(path) == digest
        record = read(path)
        assert record['passed']
        if path.name == 'nonmutation-receipt.json':
            folder = Path(record['case_folder'])
            actual = {str(p.relative_to(folder)): dict(sha256=sha(p), size=p.stat().st_size,
                       mtime_ns=p.stat().st_mtime_ns) for p in folder.rglob('*') if p.is_file()}
            assert actual == record['before'] == record['after']
            assert len(actual) == record['files']
            copy = record['copied_audit']
            assert sha(copy['path']) == copy['sha256'] == gate['verification_receipts'][copy['path']]
            cases.add(str(folder.resolve()))
        else:
            assert path.name == 'verification-receipt.json'
            folder = Path(record['source_folder'])
            source = read(folder/'record.json')
            assert record['audit'] == source['audit'] and record['audit']['physical_pass']
            for relative, item in record['tables'].items():
                original, copied = folder/relative, path.parent/relative
                assert sha(original) == item['stored_sha256']
                assert sha(copied) == item['regenerated_sha256']
                left, right = pq.read_table(original), pq.read_table(copied)
                assert left.equals(right, check_metadata=True)
                assert left.num_rows == item['rows'] and item['exact_table_schema_and_metadata']
                assert item['serialized_bytes_equal'] == (sha(original) == sha(copied))
                table_checks += 1
                serialized_differences += int(not item['serialized_bytes_equal'])
                bindings[str(copied.resolve())] = sha(copied)
    required = 4 if args.gate.name == 'preflight.json' else gate['full_period_runs']
    assert len(cases) == required
    for name,digest in bindings.items():
        assert sha(name) == digest
    report = dict(accepted_verifier_evidence=True, native_runs=0, original_case_directories=len(cases),
                  receipt_count=len(gate['verification_receipts']), exact_table_schema_metadata_checks=table_checks,
                  serialized_byte_differences=serialized_differences,
                  scope='Read-only original-case byte/size/mtime/inventory and retained copy equivalence. No numerical tolerance or native execution.',
                  bindings=bindings)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'bindings'}))


if __name__ == '__main__':
    main()
