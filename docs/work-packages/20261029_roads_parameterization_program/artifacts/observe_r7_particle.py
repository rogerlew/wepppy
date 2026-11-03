"""Exact r7, single-event observation; no production source or audit changes.

Build from the sidecar-pinned commit in an isolated directory; preserve ordinary
and observer runs, with fail-closed byte parity before arithmetic certification.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

COMMIT = 'e0abe0581f77c6f66917e90daf8f8f429e9315c8'
RECORD_SHA = '933ccbba92f5002527fa737b0ea3965a9f15e585cc8dac0606b4a089ad53be84'
BINARY_SHA = '4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825'
HILL_SHA = '210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936'
CASE = 'site-2711250-outunrut-paved-low-erosion_road_cap-project'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--native-repo', type=Path, default=Path('/workdir/wepp-forest-release-20261009'))
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(exist_ok=False, parents=True)
    shutil.copy2(Path(__file__), root / 'helper.py')
    repo = Path(__file__).resolve().parents[4]
    artifacts = Path(__file__).resolve().parent
    source = Path('/wc1/runs/ro/roads-parameterization-program-20261103/panel840-v1/cases') / CASE
    record = json.loads((source / 'record.json').read_text())
    assert sha(source / 'record.json') == RECORD_SHA
    installed = repo / 'wepp_runner/bin/wepp_261029'
    assert sha(installed) == BINARY_SHA
    assert sha(installed.with_name('wepp_261029_hill')) == HILL_SHA
    sidecar = installed.with_suffix('.json')
    assert json.loads(sidecar.read_text())['source_commit'] == COMMIT
    inputs = {**record['inputs'], **record['auxiliary_inputs']}
    for name, digest in inputs.items():
        assert sha(source / 'runs' / name) == digest
    for name, digest in record['outputs'].items():
        assert sha(source / 'output' / name) == digest
    env = {**os.environ, 'PATH': '/usr/bin:/bin:' + os.environ['PATH']}
    declaration = dict(hypothesis='Sequential REAL32 class sum and divisions explain the exact r7 printed fraction flag; test, do not assume transfer from r4.',
        case=CASE, target_event=[2003, 29], source_commit=COMMIT,
        source_record_sha256=RECORD_SHA, installed_sha256=BINARY_SHA, hill_sha256=HILL_SHA,
        sidecar_sha256=sha(sidecar), inputs=inputs, expected_outputs=record['outputs'],
        compiler=subprocess.check_output(['/usr/bin/gfortran', '--version'], text=True).splitlines()[0],
        helper_sha256=sha(Path(__file__)),
        acceptance='Both ordinary rebuilt and observer full-period outputs byte-identical to retained r7; observe terminal class state and final fractions; exact binary32 replay plus rational bound. Strict audit unchanged.',
        source_instrumentation='ENRICH cupdate.inc provides the shared event calendar; write-only, event-gated observations immediately before ENRICH class division and after SLOSS nonnegative avsole. No assignments changed.')
    dump(root / 'declaration.json', declaration)
    archive = subprocess.check_output(['git', '-C', str(args.native_repo), 'archive', COMMIT, 'src', 'fpm-src'])
    (root / 'source.tar').write_bytes(archive)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root / 'build', filter='data')
    build = root / 'build/src'
    dump(root / 'source-manifest.json', {str(p.relative_to(build)): sha(p) for p in sorted(build.rglob('*')) if p.is_file()})
    for name in ['wepp_261029.json', 'wepp_261029_hill.json']:
        shutil.copy2(repo / 'wepp_runner/bin' / name, root / name)
    shutil.copy2(source / 'record.json', root / 'source-record.json')
    results = []
    for lane in ['ordinary', 'observer']:
        if lane == 'observer':
            probes = {
                'enrich.for': ('              do 80 i = 1, npart',
                    "              if(year.eq.2003.and.sdate.eq.29)then\n"
                    "                write(*,*) 'PM_CLASS',year,sdate,iplane,kk,\n"
                    "     1            sumg,gend(1:npart),ldbot\n"
                    "              endif\n"),
                'sloss.for': ('        avsolm = avsolm + avsole',
                    "        if(year.eq.2003.and.sdate.eq.29)then\n"
                    "          write(*,*) 'PM_FINAL',year,sdate,nplane,avsole,\n"
                    "     1      frcflw(1:npart,nplane)\n"
                    "        endif\n")}
            for name, (marker, probe) in probes.items():
                p = build / name
                s = p.read_text()
                assert s.count(marker) == 1
                shutil.copy2(p, root / (name + '.original'))
                if name == 'enrich.for':
                    include_marker = "      include 'ctcfrac.inc'"
                    assert s.count(include_marker) == 1
                    s = s.replace(include_marker, include_marker + "\n      include 'cupdate.inc'")
                p.write_text(s.replace(marker, probe + marker))
                shutil.copy2(p, root / (name + '.observer'))
        command = ['make', '-j4', 'wepp', 'FC=/usr/bin/gfortran']
        with (root / (lane + '-build.log')).open('w') as log:
            subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        binary = root / ('wepp-' + lane)
        shutil.copy2(build / 'wepp', binary)
        folder = root / lane
        runs, out = folder / 'runs', folder / 'output'
        runs.mkdir(parents=True)
        out.mkdir()
        for name in inputs:
            shutil.copy2(source / 'runs' / name, runs / name)
        with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
            proc = subprocess.run([str(binary)], cwd=runs, env=env, stdin=inp, stdout=stdout, stderr=stderr, timeout=300)
        outputs = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
        result = dict(lane=lane, returncode=proc.returncode, binary_sha256=sha(binary), outputs=outputs,
                      exact_output_parity=outputs == record['outputs'], build_command=command,
                      logs={n: sha(runs/n) for n in ['stdout','stderr']})
        dump(folder / 'receipt.json', result)
        results.append(result)
        assert proc.returncode == 0 and result['exact_output_parity'], result
        for name, digest in inputs.items():
            assert sha(runs / name) == digest
    lines = [line.split() for line in (root / 'observer/runs/stdout').read_text().splitlines() if line.strip().startswith('PM_')]
    (root / 'trace.txt').write_text('\n'.join(' '.join(row) for row in lines) + '\n')
    spec = importlib.util.spec_from_file_location('certificate', artifacts / 'certify_fraction_arithmetic_u11.py')
    certificate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(certificate)
    final = [row for row in lines if row[0] == 'PM_FINAL']
    assert len(final) == 1
    fractions = list(map(certificate.real, final[0][5:]))
    assert len(fractions) == 5
    normalization = certificate.class_certificate(lines, fractions)
    avsole = certificate.real(final[0][4])
    excess = sum(map(Q, fractions)) - 1
    result = dict(declaration_sha256=sha(root / 'declaration.json'), source_archive_sha256=sha(root/'source.tar'),
        results=results, trace_sha256=sha(root/'trace.txt'), final_fractions=fractions,
        fraction_sum=float(1+excess), fraction_excess=float(excess), bulk_avsole_kg_m=avsole,
        width_m=record['width_m'], implied_excess_mass_kg=float(Q(avsole)*Q(record['width_m'])*excess),
        class_normalization=normalization, prior_certificate_helper_sha256=sha(artifacts/'certify_fraction_arithmetic_u11.py'),
        strict_audit_unchanged=True, exact_case_arithmetic_disposition='source-derived floating-point normalization residual; no implementation correction or general tolerance waiver')
    dump(root / 'result.json', result)
    dump(root / 'retention-manifest.json', {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'retention-manifest.json'})
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
