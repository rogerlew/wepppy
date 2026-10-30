# Independent implementation review: WEPP 261029

Reviewer: Codex reviewer agent `/root/implementation_review`, 2026-10-30.
This agent did not implement the candidate. This is independent AI code review,
not institutional peer review or field validation. No model source was edited.

## Findings and recommendation

No unresolved release-blocking implementation finding. Recommend technical
acceptance of the exact Linux pair below, subject to the separate scientific and
publication reviews and the remaining WEPPpy vendoring/execution gates. This
recommendation does not authorize a default change or certify general watershed
physical closure.

One low-priority documentation finding was closed during review:
`review.md`, Evidence, called the candidate-build record the current uncommitted
source. The coordinator corrected this to historical ablation provenance and
identified committed source 631aed1d1 plus exact dated-binary equivalence. Readback
confirmed the correction. No executable change or rerun was needed.

The independent scientific reviewer separately requested a qualification of the
ET explanation: the daily caller allocates only positive FIN, whereas the hourly
caller allocates signed inputs. The daily negative balance must not be introduced
as a second, unallocated withdrawal inside EVAPPM. Source inspection agrees with
that distinction; the corrected documentation does not change the patch.

## Implementation assessment

- `src/watbal_hourly.for:348` and `src/watbal.for:343` retain the complete
  local/routing sum. The removed negative branch cannot replace it with a
  runoff-only quantity. Daily channel subsurface inflow still reaches the
  existing positive-only allocator.
- `src/watbal_hourly.for:459` computes the eligible return partition in binary64.
  Its nonnegative fraction is bounded by one and uses the same local upstream
  width-times-length to receiving-area conversion as the existing hourly
  inputs. The new expression sums to the original daily exchange plus surface
  return and lateral input. It does not alter the upstream arrays or FIN.
  First elements, channels, contours and nonnegative/no-return states retain
  the preceding scheduling path. The actual mobile-stock guard at line 530
  remains active for an unfunded residual; no threshold is relaxed.
- `src/watbal.for:481` and `src/watbal_hourly.for:597` call PURK before EVAPPM;
  the hourly call occurs on the final step. Removing the extra FIN adjustment
  in `src/evappm.for:364` makes availability use current ST. The root integral
  at line 409 now preserves accumulated rooted water and adds the terminal
  rooted fraction, independently of the evaporation estimate. This is a
  shared ET change with effects beyond Roads, as the report states.
- `src/sedout.for:483` retains F7.3 for representable peaks and selects F7.2,
  then ES7.1 only on field overflow. Format 1000 still consumes seven
  characters at the same position. The retained full-fixture comparison
  changes one former asterisk field and no other output; the Roads campaign
  also exercised the real Rust importer. No ordinary field-width change is
  present.

## Independent executable checks

Ran from the canonical native checkout with the system compiler first:

    PATH=/usr/bin:/bin:$PATH \
      WEPP_HOURLY_TIMING_BINARY=/workdir/wepp-forest-release-20261009/release/wepp_261029_hill \
      pytest -q tests/test_hourly_return_timing.py tests/test_negative_fin_local_inputs.py

Result: **125 passed in 2.85 seconds**. This includes the complete committed
16-year, three-element fixture with its archive and member hashes, exact output
calendar, finite/nonnegative WAT fields, positive area and sediment/runoff checks.
The source-block probes execute the actual production expressions; the negative
inventory test still requires a native failure.

Also independently compiled the production partition and scheduling blocks with
`/usr/bin/gfortran -O2`. All 48 combinations passed: FIN values -0.08, -0.02, zero
and +0.02 m; upstream/receiving `(width, length)` combinations giving area ratios
1, 8/15 and 30; contour flag zero/one; and hillslope/channel version. Surface
return occurred in two separated hours (0.01 and 0.03 m) with 0.0001 m lateral
input every fourth hour. Compared each hour and daily sum to an independent
binary64 equation using rounded binary32 input values, within 5e-7 times the
absolute input magnitude (floor 1e-12 m). Fully return-funded eligible cases had
no negative hourly exchange. This supplemental probe is review evidence, not a
new permanent regression requirement.

## Source, binary and evidence identity

Verified the current changed model files, their `git show 631aed1d1:<path>`
contents and retained candidate source hashes agree. The branch matches
`origin/HEAD`: `wepp_260430_negmeltfix_comparator`. Both dated executable hashes
match the historical scientific candidate and adjacent sidecars exactly:

- Source: `631aed1d1c89ed8fa76c5dc3f2e4258a8f199504`.
- Watershed: `53628775e0e97d03f3f8c12e0d99b0f25842efa429d3ce869bf37ee382974461`.
- Hillslope: `080adc9b7b4065f5cba2c2b290369121ea76c042693b74b616ff651117457cd4`.

Verified every log checksum in WEPPpy release work-package
`artifacts/prepromotion-gates.json`. Inspected retained fresh native results:
663 tests passed, two deprecation warnings, 13/13 watchlist cases, both host
smokes, both scratch-path container smokes, artifact policy and compatible ELF
provenance. These broad gates were run by the implementing coordinator, not
repeated by this reviewer. The exact binary identity validly carries forward
Roads, Disturbed and Cedar evidence without pretending they were rerun here.

## Residual risk and coverage limits

The proportional return attribution remains a model approximation. Algebraic
conservation and correct implementation do not prove physical timing for every
geometry or mixed source. The separate scientific review owns that acceptance.
The 96 Roads configurations are a development screen, not withheld soils or
field calibration. Full-record and event effects outside Roads remain material
review evidence. Daily negative-allocation limitations and wider signed
soil/channel coupling remain explicitly open.

The reviewer did not rerun the full Roads, Disturbed or Cedar studies, native
Windows parity, or post-vendoring HTTP/selected-release integration. No Windows
release is recommended here. Repeat relevant validation if model source, build
flags, compiler or binary hashes change; documentation-only corrections do not
invalidate this exact-pair implementation review.

## Independent WEPPpy integration addendum, 2026-10-30

Reviewer: the same independent implementation-review agent. No integration blocker
found. This addendum concerns the final vendored files and retained actual runtime
artifacts, not an additional native model revision. The native release was
committed as 47183b0fb; executable source identity remains 631aed1d1.

Independently rehashed both `wepp_runner/bin/wepp_261029` profiles and compared
both JSON sidecars byte-for-byte with the native `release/` copies. Every file
matches. The binary SHA256 values remain the exact reviewed pair above; capability
and ASCII PASS-v3 metadata agree with the runtime check.

Read `verify_selected_release.py`, its retained log and receipt, and the actual
`/wc1/ablation/hourly-return-timing-20261030/selected-release-runtime-v3` artifacts.
The script calls production discovery/capability resolution, selects the hill
profile through `run_hillslope`, checks the traceability log against its binary
hash, and invokes the production Rust ELEMENT/WAT importers. Independently
verified all seven raw output hashes and the runner-log hash against the receipt;
readback confirms the selected dated hill path and hash, with no retry. The
scratch receipt matches the retained release receipt exactly.

Independently reread all 17,532 raw WAT records: exact expected calendar across
16 years and three OFEs, finite/nonnegative physical columns and positive area.
Both Parquet outputs have the recorded row counts, 3,237 ELEMENT event records
and 17,532 WAT daily records. All provided floating fields are finite; the absent
optional `InterceptionStorage` remains null. Additionally compared all 22 numeric
ELEMENT fields for every event against the native text using OFE/date keys:
all values match exactly, including the repaired peak field with maximum
1176.00 mm/hour. Thus the parser evidence checks actual values as well as counts.

The two corrected harness assumptions are appropriate: ELEMENT reports selected
events, while WAT reports daily rows; an optional field absent from the producer
must remain unknown. `artifacts/validation.md` discloses those initial failures.
Neither correction changes the native artifacts or relaxes a physical threshold.

Inspected the post-vendor provenance and both host/container smoke logs, plus the
69-passed targeted test log. Release-policy test changes add 261029 to both
old-provider exclusion and explicit save/reload coverage; capability snapshots
include the newly installed pair. They preserve prior releases and exercise
saving a newly discovered binary without rewriting old project configuration.
There is no production Python logic change in this promotion.

Reviewed identities for reproducibility:

- Verification script SHA256: `2b7269c31d96c8d8c8d161b8a000dabd129a2c1887c405b361bf196a4f946269`.
- Runtime receipt SHA256: `0993a2ae626aa1f59054130a25f8c1cb09ce5ff9a91ab6739727ae3ddd93f0cc`.
- Targeted test log SHA256: `b4e58383153c8601b347450614776f26824cf292c9759e1f22969a8f3ec4ee21`.

The 69-test execution was inspected, not duplicated. The reviewer did not restart
the full WEPPpy suite, which was still running when this addendum was written;
its required completion remains with the coordinator. The selected-release
fixture specifically executes the hillslope profile; the complete matched
watershed execution is supported by the previously reviewed Cedar evidence.
HTTP/publication review remains a separate artifact. No production deployment or
default change is inferred from these checks.
