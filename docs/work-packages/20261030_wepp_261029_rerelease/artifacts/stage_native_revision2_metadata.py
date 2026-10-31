"""Prepare native revision-2 sidecars with science/downstream gates pending.

Run only while staging this release; final acceptance is a separate action.
"""
import hashlib
import json
from pathlib import Path
import subprocess

RAW = Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
REPO = Path('/workdir/wepp-forest-release-20261009')
ARTIFACTS = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    preflight = json.loads((ARTIFACTS/'native-build-preflight.json').read_text())
    candidate = json.loads((RAW/'U9a-provenance.json').read_text())
    source_manifest = candidate['declaration']['source_sha256']
    for name, expected in source_manifest.items():
        assert sha(REPO/name) == expected, name
    manifest = ARTIFACTS/'native-source-manifest.json'
    manifest.write_text(json.dumps(source_manifest,indent=2,sort_keys=True)+'\n')
    pair = {name:sha(REPO/'release'/name) for name in ['wepp_261029','wepp_261029_hill']}
    smokes = (RAW/'261029-r2-smokes.log').read_text()
    assert smokes.count('rc=0\tsuccess=1') == 2
    watch = (RAW/'261029-r2-watchlist.log').read_text()
    assert 'summary\tpassed=18\tfailed=0' in watch
    result = {}
    for name in pair:
        path = REPO/'release'/(name+'.json')
        data = json.loads(path.read_text())
        original_path = RAW/'original-native-261029-pair'/(name+'.json')
        original = json.loads(original_path.read_text())
        assert data['source_commit'] == preflight['source_commit']
        assert data['features'] == original['features']
        assert data['sha256'] == pair[name]
        data['artifact_revision'] = 2
        data['release_status'] = 'staged; scientific and downstream acceptance pending'
        data['supersedes'] = dict(artifact_revision=1,sha256=original['sha256'],
                                   sidecar_sha256=sha(original_path),source_commit=original['source_commit'])
        data['matched_pair_sha256'] = pair
        for field in ['capacity','execution_calendar','math_runtime','paired_interchange']:
            data[field] = original[field]
        data['build'] = dict(compiler='/usr/bin/gfortran',
                            compiler_version=subprocess.check_output(['/usr/bin/gfortran','--version'],text=True).splitlines()[0],
                            assembler='/usr/bin/as',linker='/usr/bin/ld',
                            binutils_version=subprocess.check_output(['/usr/bin/ld','--version'],text=True).splitlines()[0],
                            path_prefix='/usr/bin:/bin',
                            source_manifest_sha256=sha(manifest),
                            source_manifest_files=len(source_manifest),
                            build_log_sha256=sha(RAW/'261029-r2-dated-build.log'),
                            runtime_source_checkpoint='d32cc5f86',
                            subsequent_tooling_fix='391e7327f; no rebuild, same PATH already used')
        data['known_limitations'] = [
            'Scientific acceptance of final watershed sediment attribution remains pending.',
            'Signed soil/channel withdrawal acceptance, negative-discharge clipping and Muskingum-Cunge storage authority remain separate open limitations.',
            'Hourly return partition and late-source support describe the existing model time support, not a travel-time solver or independently reconstructed physical hydrograph.',
            'Connected melt repair excludes channels and retains mixed-rain precedence, zero-local-melt and absolute-clock limitations.',
            'Storage subtotal repair preserves the existing contributing set; channel processing-order membership and upstream state freshness are not redefined.',
            'Constant-discharge channel transport retains segment-average width, linear capacity, existing onset and cohort/DETACH handoff approximations.',
            'The existing large-top-flow hydraulic guard retains its threshold and limiting approximation; full hydraulic continuity is not claimed.',
            'Historical top/lateral sediment unit-conversion differences remain unchanged.',
            'Roads magnitude remains 749/840 on the experimental development panel, below frozen acceptance thresholds; no field calibration or withheld-soil acceptance.',
            'This same-name reissue requires regenerated hillslope/PASS/watershed outputs with the exact matched pair; revision-1 bytes are incompatible study identities.',
            'No new Windows release, default switch or production deployment is claimed.',
        ]
        data['validation'] = dict(host_smoke='both dated profiles passed three configured years',
                                 hillslope_watchlist='18 passed; zero failures on dated hill binary',
                                 binary_provenance='pass; system ELF interpreter and libraries',
                                 elf_interpreter='/lib64/ld-linux-x86-64.so.2',
                                 pytest='fresh system-toolchain run pending',
                                 roads_development_panel='fresh 840-case system-toolchain run pending',
                                 disturbed_matrix='fresh system-toolchain run pending',
                                 same_build_watershed_replay='fresh system-toolchain Cedar run pending',
                                 release_candidate_equivalence='not claimed; different binutils changes padding and ELF loader metadata; actual dated bytes revalidated',
                                 independent_scientific_review='pending',
                                 independent_implementation_review='bounded model review complete; actual dated-byte final gates pending',
                                 downstream_vendoring='not performed; installed WEPPpy revision 1 unchanged',
                                 selected_release_runtime='not run for revision 2',
                                 release_report='revision 2 draft; publication pending',
                                 production_deployment='not performed')
        temporary=path.with_suffix(path.suffix+'.staging')
        temporary.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
        temporary.replace(path)
        result[path.name]=sha(path)
    installed=Path('/workdir/wepppy/wepp_runner/bin')
    assert {name:sha(installed/name) for name in preflight['installed_sha256']} == preflight['installed_sha256']
    (ARTIFACTS/'native-revision2-staging.json').write_text(json.dumps(dict(binary_sha256=pair,
        sidecar_sha256=result,source_commit=preflight['source_commit'],science='pending',
        installed_revision1_unchanged=True,script_sha256=sha(Path(__file__))),indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
