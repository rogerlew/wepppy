# C05/C06 Geneva implementation security review

**PASS for this bounded implementation review: G-I01 through G-I04 are closed.**
Performance, supported identity/group parity and full runtime gates remain open.
Review compares the uncommitted implementation with checkpoint `31f77bef1`.
Reviewer: `freshness_security`. Only disposable probes and this review record
were written; no production/tests or named project data were edited.

## Findings

**G-I01, medium, closed below: native publication adds an incompatible
inode-write requirement.** `_Attempt.publish` initially called nontruncating
`O_WRONLY` for both writers. Under actual UID 1000 with a writable parent and
mode-0444 target, the existing `raster_stacker` successfully replaces the TIFF,
while the new alignment service raised `GenevaValidationError` and retained old
class-1 pixels. `geneva_security_readonly_native.json` retains both native results.
This is a concrete valid-workflow permission regression, not a privilege gain.
Preserve the JSON writer's inode-write authorization but do not impose it on the
native writer, which uses directory replacement authority. The parent reports
the condition is now consumer-specific; after-probe remains pending.

**G-I02, medium, closed below: publication selection and clean-layout
checks precede the final validation callback.** The callback performs filesystem
observations and can overlap observable target changes. Two actual native
controls demonstrate accepted wrong-boundary publication:

- Retargeting the canonical output symlink after the callback's dependency
  checks causes the old resolved target to be overwritten, returns success and
  leaves the newly selected target unchanged. The output link itself remains
  changed (`geneva_security_late_alias_tiff.json`).
- Creating an external mask after those checks causes a newly published class-3
  TIFF to read with mask values 0. Main-file replacement preserves the newly
  introduced mask (`geneva_security_late_mask.json`). This is the same concrete
  sidecar effect that motivated the clean-target checkpoint.

Recheck selected target and eligible clean membership after the callback,
immediately before replacement. Keep the native compatibility branch for an
auxiliary layout present at initial selection; a late transition must reject
with `changed_source` and preserve prior accepted main bytes, not switch into a
destructive fallback after candidate generation. These guards detect observed
changes and are not arbitrary-writer isolation. The parent reports both final
checks and the TIFF-hit selection check are implemented; verification is pending.

**G-I03, low, closed below: absent main file incorrectly implies clean
target layout.** `clean_tiff_proof` returns clean on FileNotFoundError before
inspecting orphan companions. With a retained external mask but absent target
main, the service publishes a candidate and earned proof rather than taking the
explicitly unverified native compatibility branch. Actual old and new writers
both return mask 0 in this fixture: this is not a new numerical divergence or
authority expansion. It is a confirmed boundary-classification/provenance
violation. Inspect the already authorized finite companion layout for an absent
selected main; do not claim absence proves no companions or add a general
inventory. The parent reports this is corrected using the existing filename
inventory, without added native opens.

**G-I04, low, closed below: a post-commit resolver error is reported as
publication failure.** Replacing `status.json` with a symlink outside the Geneva
root after the actual candidate replace makes the existing resolver correctly
raise ValueError. The diagnostic exit boundary catches only OSError; the service
therefore raises `invalid_input` despite committed class-3 output. The outside
record remains unchanged: containment works. Log the expected resolver failure
at the minimal status boundary without undoing or misreporting the commit. The
parent reports the boundary now catches OSError and ValueError only.

## Initial evidence and passing controls

Command:

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/geneva_implementation_security_probe.py -v -s
```

`geneva_implementation_security_probe.log`: **4 failed, 3 passed in 9.38 s**.
Three failures are the findings above. The fourth, GeoJSON alias testing, did not
reach publication: the probe's nodata-free raster yields a scalar mask rejected
by the preexisting `shapes` path. It is not evidence of a new implementation
defect. Revision2 supplies explicit nodata=0; the initial script/log/results
remain intact.

Passing controls use actual native operations: existing external-mask targets
take the compatibility overwrite path and return class 3 with valid mask 255;
stable selected output symlinks remain symlinks and preserve modes 0600/0640;
new attempt leaves are 0700 and status files 0600. These controls do not establish
all group/ownership, mount, confinement or archive/runtime acceptance.

## Review scope and remaining gates

The implementation uses content proofs with separate physical read guards,
private retained attempts, the existing ArtifactIO root resolver and typed
changed-source errors. The helper's `check_unchanged` can bind additional legend
or bound-profile reads to an existing acquisition without extra native discovery.
Correctness review independently covers native dependency/legend/profile
coherence and valid numerical behavior. This security review owns publication
selection, access and retained-artifact boundaries.

Before final scoped approval, verify the fixes with the real service paths,
complete read/access and failure-retention checks, and bind the reviewed source
hashes. Representative timings, production-equivalent identities/groups/mounts,
normal route/kernel execution and browse/archive/restore remain package gates.

## Independent correction verification

`geneva_implementation_security_probe_revision2.py/.log`: **7 passed in 9.64 s**.
This retains the original failed probe separately and corrects only its GeoJSON
fixture nodata assumption. Actual writer/publication behavior now passes:

- The native 0444 target rebuild succeeds; the JSON-specific authorization
  remains intact. G-I01 is closed.
- Both JSON and TIFF late output-link changes return `changed_source` while
  preserving both prior target files. A late mask rejects before candidate
  replacement and leaves the prior main pixels intact. G-I02 is closed.
- Existing-mask native compatibility and stable selected symlinks with modes
  0600/0640 continue to pass, with private attempt/status modes.

`geneva_failure_security_probe.py/.log` retains the later **2 failed, 2 passed in
9.44 s** characterization of G-I03/G-I04. The distinct revision2 script/log
passes **5 tests in 9.28 s** after correction:

- The absent-main/orphan-mask case takes original native overwrite, preserves
  native mask behavior and records the compatibility branch rather than
  publishing new verified proof. The finite ordinary filename scan adds no
  native open or broader path authority. G-I03 is closed.
- The actual outside-root status symlink is still rejected by ArtifactIO, the
  unrelated outside record is unchanged, and the minimal diagnostic boundary
  logs ValueError without misreporting the committed output. G-I04 is closed.
- A denied existing TIFF cache read fails and keeps prior bytes. A readable
  0444 JSON target still raises PermissionError and retains prior bytes.
- A cached GeoJSON target in a separate output directory disappearing after
  the cache read now returns `changed_source`, including when the raster's
  scanned parent itself did not change.

The parent also added failure-path input validation. Independent correctness
review reports 12 actual native controls passing, including removed legend/source
and preserved stable native validation errors; that evidence is complementary
to this publication/access review. No unresolved medium/high scoped finding
remains. All initial failing evidence is retained without relabeling it a pass.

Reviewed production SHA-256 values:

```text
_cache_freshness.py 63f87911d2ce5a397776e06eaac5a34cc5d776b504551e81da033b381a02c789
hru_map_geometry_service.py 98c3f8c3b67abd21c10aacf9c0b278df1874a07c2a2684c038f18f6bbfa51034
hsg_assignment_service.py 295afbf2e63cdacb2b688f9adf7b52f7defc2b81dcb4dec6eff8aadb78775a67
```

These disposable controls ran as UID 1000. They establish the tested file modes,
selection, error and native boundaries, not arbitrary mixed-owner/group, ACL or
mount compatibility. The candidate chown path requires final supported service
identity/group evidence; mode tests alone do not certify it. No runtime rollout,
route/kernel end-to-end acceptance or archived-attempt restoration is implied.

Subsequent canonical archive characterization found private directory modes are
not recorded/restored. See `archive_attempt_permissions_security_review.md`:
A-S01 remains an open cross-wave runtime integration gate. This producer review
does not waive that finding or claim whole-package permission parity.

## C06 same-call verification refinement

The final optimization remains conformant: full source/bound observations and
the actual effective bound-profile read occur on every call. Subsequent checks
reuse only that call's proven graph, run all physical/config guards before and
after the complete set, verify every captured resolved path and SHA through the
existing digest admission policy, and rescan companion membership. Recent files
therefore keep byte verification; this is not the rejected stat-only shortcut.
Known disappearance/access errors during these already-observed reads become
`changed_source`, while unrelated EIO propagates. No graph survives into another
request and no new native discovery authority is introduced.

The private candidate resolver uses the already validated attempt root while
still enforcing basename/member containment; final canonical destination checks
remain in ArtifactIO. The independent correctness revision3 log records
**15 passed in 9.78 s**, including joint source mutation during bound hashing,
removal between physical guard and digest, and preserved unrelated EIO, alongside
the prior native/ABA/error controls. Scoped security PASS remains; the retained
performance misses require separate QA disposition and actual acceptance.

Reviewed optimized SHA-256 values:

```text
_cache_freshness.py 405223512fbf699d35d008bdb0228802ee2a39b2095dfc8ed3f67b3521b8e2b1
hru_map_geometry_service.py 98c3f8c3b67abd21c10aacf9c0b278df1874a07c2a2684c038f18f6bbfa51034
hsg_assignment_service.py 59ee01affee3b9455327868d17f4b76191d622ef2c520f7307f480fe706da96f
```
