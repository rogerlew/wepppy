# Reproduction record

Internal reproduction requires authorized access to WEPP-Forest and forest's
archived Topanga fixtures. Do not execute these scripts against a live project
directory. All generated files belong in a fresh isolated study root.

## Build provenance

- WEPPpy source/tools: `35cfc8ec5b07cc712c22c483b6f77763f349ad1a`.
- WEPP-Forest source: `ea25ad79ef7dab20206bca095b2958786f5ae317`.
- Compiler: GNU Fortran (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0.
- Exported pinned `src` and `fpm-src`; no source edits or shared-worktree build.
- Observer: `make -C source/src wepp_hill`, serial compilation.
- Flags from actual log: `-fno-align-commons -mcmodel=medium -g -fbacktrace -O2
  -ffpe-trap=invalid,zero,overflow -finit-local-zero`; fixed-form sources also
  `-ffixed-form -ffixed-line-length-72`; link `-mcmodel=medium -no-pie -lz`.
- Initial build lacked `fpm-src`; a parallel retry exposed Fortran module-order
  dependency. Both failed logs remain on forest; serial build passed. These
  were isolated build failures, not model-result failures.
- Observer SHA-256:
  `36f3560395676e6a4f96d4eff87e3a860e8c6172efd76fdcb8985d817d8a9047`.
- Replay SHA-256:
  `3dcacd6c694ac4e233a18b79ffb0055a7e7a8cf12c94e72ac8dc8106129022b2`.

Replay used the unchanged driver from
`docs/work-packages/20260808_peakflow_phase1/artifacts/peak_replay_driver.for`:

```sh
gfortran -O2 -mcmodel=medium -fno-align-commons \
  -ffpe-trap=invalid,zero,overflow -finit-local-zero \
  -Iincludes_hill -I. /path/to/peak_replay_driver.for \
  appmth.for hdrive.for bgnrnd.for hdepth.for phi.for psiinv.for \
  sint.for psis.for rand.for sintdp.for -o /path/to/peak_replay
```

The old protocol build IDs are retained for historical packet-hash checking;
`rebuild-identities.json` explicitly distinguishes the rebuilt executable
hashes from the historical binaries. They must not be represented as the same
executable. Forest retains `build.log`, `build-retry.log` and `build-serial.log`
under `/home/workdir/topanga-seed-recurrence-20261006`.

## Actual execution sequence

Cluster runtime: Python 3.12.13 (GCC 14.2.0), Linux 6.18.48-talos x86_64,
glibc 2.41, NumPy 1.26.0, pandas 2.2.2 and PyArrow 23.0.1. Forest compilation
and cluster execution are intentionally distinguished by the parity record.

1. `prepare.py` froze five input decks, climate source, tools and seed list.
2. Build observer/replay as above; `accept.py` passed the historical gate on
   forest, including exact packets and inactive/active observer parity.
3. Stage the bundle on openwepp, run `python study.py control --workers 1`,
   compare to forest, and retain `cross-host-parity.json`. Repeat the unchanged
   original control independently to establish same-host byte parity.
4. `python check_gates.py control` and climate reconstruction checks passed.
5. `python study.py pilot --workers 4`, then `python check_gates.py pilot`.
   Rejected initial quality-guard attempts remain under `attempts/`.
6. `python study.py inference --workers 4` submitted exactly the frozen 100
   seeds. Its initial exit was nonzero after two climate-name rejections;
   already-submitted tasks completed. No final analysis ran from that failure.
7. `python retry_daily_warnings.py` preserved the two rejected attempts and
   reran the same seeds, requiring identical raw climate hashes. This script
   is a one-time recovery record, not a generic retry wrapper; its guards
   deliberately reject other circumstances.
8. `python analyze.py`, `python figures.py`, `python audit_results.py` compute
   and validate final artifacts. `python script_checks.py` supplies focused
   arithmetic, boundary, date and missing-event regression checks.
9. Original replay had five mismatches/failures. Inspecting pinned IRS showed
   its storm-only branch overwrites `remax`, while the old replay always used
   the captured pre-surplus value. `python branch_replay.py` adds separate
   source-checked production-operand reports, retaining all original failures.
   Its first invocation had an incorrect import; the error log was preserved,
   the import corrected, and all 20 lane cases then matched exactly. Figures
   and artifact audit were rerun to include this evidence. Final reproduction
   must run `branch_replay.py` before the final `audit_results.py`.

Do not rerun into populated output directories: creation guards intentionally
fail. Reproduction should use a new isolated root and preserve old artifacts.
The scripts' explicit forest paths identify this recorded execution; adapt
only the staging root for a new run and retain the resulting provenance.
`cross-host-parity.json` records the original comparison, not permission to
skip fresh parity when changing host, toolchain or executable.

## Recovery and publication boundary

Raw diagnostic traces and canonical outputs are losslessly gzip-compressed
after their original hashes are captured. The final audit decompresses and
rehashes every inference output. Public artifacts exclude model executables,
restricted source, source-project private state and bulk output. The public
storage index permits authorized retrieval and integrity checking of those
retained internal artifacts. No automatic deletion or service mutation is
part of recovery.
