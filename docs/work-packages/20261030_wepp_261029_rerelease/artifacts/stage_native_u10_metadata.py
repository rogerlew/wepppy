"""Freeze scientifically accepted native U10 identity before downstream vendoring."""
import hashlib
import json
from pathlib import Path

RAW=Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
REPO=Path('/workdir/wepp-forest-release-20261009')
ARTIFACTS=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    provenance=json.loads((RAW/'U10-provenance.json').read_text())
    declaration=provenance['declaration']
    science_path=REPO/'docs/ablation/20261030_roads_daily_coupling_and_event_state/artifacts/repro/review-U10-final-scientific-acceptance.json'
    science=json.loads(science_path.read_text())
    assert science['disposition']=='ACCEPT final U10 native scientific repair within documented scope'
    assert science['source_commit']==declaration['source_commit']
    assert science['pair']==provenance['binary_sha256']
    assert science['frozen_and_current_source_hashes_match']
    for path,expected in science['evidence_sha256'].items():
        assert sha(Path(path))==expected,path
    broad=json.loads((ARTIFACTS/'native-U10-broad-gates.json').read_text())
    assert broad['binary_sha256']==provenance['binary_sha256']['wepp']
    assert broad['source_commit']==declaration['source_commit']
    assert broad['roads_completed']==broad['roads_physical_pass']==840
    assert broad['roads_inputs_verified']==10080 and broad['roads_outputs_verified']==5880
    assert broad['roads_magnitude_within']==749 and not broad['roads_parameterization_accepted']
    assert broad['roads_magnitude_groups']=={'meaningful':{'cases':766,'within':719},'small':{'cases':74,'within':30}}
    assert broad['disturbed_tests_passed']==99 and broad['disturbed_outputs_retained']==768
    for name,expected in declaration['source_sha256'].items():
        assert sha(REPO/name)==expected,name
    manifest=ARTIFACTS/'native-u10-source-manifest.json'
    manifest.write_text(json.dumps(declaration['source_sha256'],indent=2,sort_keys=True)+'\n')
    pair={name:provenance['binary_sha256'][profile] for name,profile in
          [('wepp_261029','wepp'),('wepp_261029_hill','wepp_hill')]}
    original_snapshot=json.loads((ARTIFACTS/'native-build-preflight.json').read_text())
    installed=Path('/workdir/wepppy/wepp_runner/bin')
    assert all(sha(installed/n)==h for n,h in original_snapshot['installed_sha256'].items())
    staged={}
    for name,expected in pair.items():
        binary=REPO/'release'/name;assert sha(binary)==expected
        path=binary.with_suffix('.json');data=json.loads(path.read_text())
        assert data['source_commit']==declaration['source_commit']
        assert data['source_branch']==declaration['source_branch']
        assert data['sha256']==expected
        original_path=RAW/'original-native-261029-pair'/(name+'.json')
        original=json.loads(original_path.read_text())
        assert data['features']==original['features']
        data['artifact_revision']=2
        data['release_status']='revision 2 native repair accepted; downstream integration, publication and deployment are tracked separately'
        data['supersedes']=dict(artifact_revision=1,sha256=original['sha256'],
                               sidecar_sha256=sha(original_path),source_commit=original['source_commit'])
        data['matched_pair_sha256']=pair
        for field in ['capacity','execution_calendar','math_runtime','paired_interchange']:
            data[field]=original[field]
        data['math_runtime']['native_double_calls']='unwrapped system libm; stable deposition and Yalin factors use double intermediates'
        data['build']=dict(toolchain=declaration['toolchain'],path_prefix='/usr/bin:/bin',
                           source_manifest_sha256=sha(manifest),source_manifest_files=len(declaration['source_sha256']),
                           build_script_sha256=declaration['build_script_sha256'],
                           build_log_sha256=provenance['build_log_sha256'],
                           native_provenance_sha256=sha(RAW/'U10-provenance.json'),
                           fixture_first_commit='a8780759b',independent_test_commit='2934a24b8')
        data['validation_evidence']=dict(
            native_gate_logs_sha256=json.loads((ARTIFACTS/'native-U10-gates.json').read_text())['logs_sha256'],
            broad_gate_receipt_sha256=sha(ARTIFACTS/'native-U10-broad-gates.json'),
            scientific_acceptance_path=str(science_path.relative_to(REPO)),
            scientific_acceptance_sha256=sha(science_path),
            scientific_review_path='docs/work-packages/20261030-roads-native-accounting/artifacts/U10-Yalin-independent-scientific-review.md',
            scientific_review_sha256='7a239ac7ed5f50f848296b0219bd218f61bcd1a263d136842909c2b81767359b')
        data['known_limitations']=[
            'Scientific acceptance is bounded by the retained mathematical and native controls, full-period class sign/finiteness audit, and sixteen-date local source/bed audit; it does not establish whole-watershed sediment closure or measured-sediment calibration.',
            'Signed soil/channel withdrawal acceptance, negative-discharge clipping and Muskingum-Cunge storage authority remain separate open limitations.',
            'Hourly source-time return partition and late-source support are not a travel-time solver or independently reconstructed physical hydrograph.',
            'Connected melt repair retains mixed-rain precedence, zero-local-melt and absolute-clock limitations; channel indices are excluded from that melt repair.',
            'Storage subtotal repair preserves the existing contributing set and does not redefine channel processing-order membership or upstream state freshness.',
            'Channel transport retains segment-average width, linear capacity, onset/cohort handoff, hydraulic limiting guard and historical unit-conversion approximations.',
            'The stable Yalin factor applies to hillslope and channel capacities; correcting one negative class can change allocation for all classes. Fresh outputs were validated; complete output parity with the preceding candidate is not claimed.',
            'Cedar outlet sediment is 517815.77 kg versus original revision 1 180137.20 kg (+187.456%); annual changes range from -0.303% to +1286.54%. These material changes require release-note disclosure and are not calibration evidence.',
            'Fresh U10 Roads magnitude acceptance fails in both separate groups: meaningful-reference cases 719/766 (93.864%) and small-reference cases 30/74 (40.541%); each requires 95% overall and 90% per declared major stratum. The 749/840 aggregate is descriptive only. No field calibration, parameterization acceptance or withheld-soil acceptance is claimed.',
            'Regenerate all contributing hillslope/PASS/watershed outputs with the exact matched replacement pair, not the shared tag alone.',
            'No new Windows release, project default switch or production deployment is claimed.',
        ]
        data['validation']=dict(
            host_smoke='pass; both actual U10 dated profiles complete the three-year host fixture',
            hillslope_watchlist='18/18 pass on actual U10 dated hillslope binary',
            binary_provenance='pass; actual U10 system loader and runtime libraries',
            elf_interpreter='/lib64/ld-linux-x86-64.so.2',
            focused_capacity_controls='80 checks pass at O0/O2, including 1152 frozen consumer inputs and exact unequal-class Cedar state',
            pytest='1059 passed, 2 existing tarfile deprecation warnings in 615.74 seconds on actual U10 source/pair',
            artifact_policy='pass; native ablation size and retention policy',
            roads_development_panel='840/840 native completion and physical/accounting audit pass on U10; separate magnitude gates remain unmet: 719/766 meaningful-reference cases and 30/74 small-reference cases; 749/840 aggregate is descriptive only',
            disturbed_matrix='99 tests pass, covering 96 actual U10 hillslope simulations; 768 native output hashes retained',
            same_build_watershed_replay='pass; 864 freshly generated hillslopes and 24-year U10 Cedar watershed, all PASS/WAT conversion and physical/particle checks, nine-output observation parity, zero full-period negative/nonfinite intermediate class transfers',
            channel_source_bed_audit='pass within declared sixteen dates: 5936 channel-events, 29680 source-class records; source relative residual at most 1.8392e-7, local closure relative scale at most 3.5307e-8, exact segment joins',
            independent_implementation_review='pass; independent AI source/math, actual-byte local gates and frozen-input broad-evidence verification',
            independent_scientific_review='accepted by independent AI review for the exact matched pair within documented scope; material sediment changes must be disclosed; not institutional peer review or measured calibration',
            downstream_vendoring='Separate integration evidence is maintained in WEPPpy docs/work-packages/20261030_wepp_261029_rerelease; not included in native validation counts',
            selected_release_runtime='Recorded separately by the WEPPpy re-release integration workflow',
            release_report='Revision 2 scientific report and publication evidence are tracked separately in docs/release-notes/wepp_261029/publication-manifest-r2.json',
            production_deployment='No deployment is certified by this native metadata')
        temporary=path.with_suffix('.json.staging')
        temporary.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');temporary.replace(path)
        staged[path.name]=sha(path)
    receipt=dict(source_commit=declaration['source_commit'],binary_sha256=pair,sidecar_sha256=staged,
                 source_manifest_sha256=sha(manifest),script_sha256=sha(Path(__file__)),
                 installed_revision1_unchanged=True,
                 acceptance='Accepted native revision 2; sidecars frozen for downstream integration. Scientific scope limits and separate publication/deployment evidence remain explicit.')
    (ARTIFACTS/'native-U10-revision2-staging.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(staged,indent=2))


if __name__=='__main__':main()
