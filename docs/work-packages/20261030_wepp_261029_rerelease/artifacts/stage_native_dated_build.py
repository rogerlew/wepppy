"""Stage the authorized native 261029 revision without WEPPpy vendoring."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path('/workdir/wepp-forest-release-20261009')
RAW = Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
ARTIFACTS = Path(__file__).resolve().parent
EXPECTED_COMMIT = '2b4cd9fb52510d7ff9fbd79e657050efe06baed1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, text=True).strip()


def main():
    branch = git('branch', '--show-current')
    remote = git('symbolic-ref', 'refs/remotes/origin/HEAD')
    assert remote == 'refs/remotes/origin/' + branch
    assert git('rev-parse', 'HEAD') == EXPECTED_COMMIT
    original = RAW / 'original-native-261029-pair'
    original.mkdir(exist_ok=True)
    files = ['wepp_261029', 'wepp_261029_hill',
             'wepp_261029.json', 'wepp_261029_hill.json']
    preserved = {}
    for name in files:
        source = REPO / 'release' / name
        target = original / name
        if not target.exists():
            shutil.copy2(source, target)
        assert sha(source) == sha(target), name
        preserved[name] = sha(target)
    candidate = json.loads((RAW / 'U9a-provenance.json').read_text())
    assert {n: preserved[n] for n in candidate['installed_sha256']} == candidate['installed_sha256']
    for name, expected in candidate['declaration']['source_sha256'].items():
        assert sha(REPO / name) == expected, name
    installed = Path('/workdir/wepppy/wepp_runner/bin')
    installed_before = {n: sha(installed / n) for n in files}
    preflight = dict(source_commit=EXPECTED_COMMIT, source_branch=branch,
                     remote_default=remote, source_files_verified=506,
                     candidate_manifest_sha256=sha(RAW / 'U9a-provenance.json'),
                     original_native_directory=str(original),
                     original_native_sha256=preserved,
                     installed_sha256=installed_before,
                     command='TARGET_TAG=261029 COMPILER=/usr/bin/gfortran SOURCE_COMMIT=' + EXPECTED_COMMIT + ' tools/build_wepp_dated_release.sh',
                     science_status='pending; native staging only')
    (ARTIFACTS / 'native-build-preflight.json').write_text(json.dumps(preflight, indent=2) + '\n')
    env = dict(os.environ, TARGET_TAG='261029', COMPILER='/usr/bin/gfortran',
               SOURCE_COMMIT=EXPECTED_COMMIT, SOURCE_BRANCH=branch,
               PATH='/usr/bin:/bin:' + os.environ['PATH'])
    try:
        with (RAW / '261029-r2-dated-build.log').open('w') as log:
            subprocess.run(['tools/build_wepp_dated_release.sh'], cwd=REPO,
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    finally:
        subprocess.run(['make', '-C', 'src', 'prepare_watershed_includes'],
                       cwd=REPO, env=env, check=True)
    for name, expected in candidate['declaration']['source_sha256'].items():
        assert sha(REPO / name) == expected, name
    assert {n: sha(installed / n) for n in files} == installed_before
    print(json.dumps({n: sha(REPO / 'release' / n) for n in files}, indent=2))


if __name__ == '__main__':
    main()
