# Release Checklist (wepp-forest)

Use this checklist for every binary release/vendoring cycle.

## Pre-Release

1. Confirm target change scope and version tag (`wepp_<tag>`).
2. Rebuild binaries with pinned system `gfortran` resolution:
   ```bash
   unset FC F77 LINKER
   hash -r
   cd /workdir/wepp-forest/src
   make clean
   make COMPILER=gfortran wepp
   make COMPILER=gfortran wepp_hill
   make -pn wepp_hill | rg "^(COMPILER|FC|LINKER) ?="
   ```
   Required in build metadata:
   - `COMPILER = gfortran`
   - `FC`/`LINKER` resolve to `/usr/bin/gfortran` (not Homebrew)
3. Run required quality gate:
   ```bash
   cd /workdir/wepp-forest
   tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp
   tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill
   pytest
   ```
4. Verify ELF interpreter path on both binaries:
   ```bash
   readelf -l /workdir/wepp-forest/src/wepp | rg "Requesting"
   readelf -l /workdir/wepp-forest/src/wepp_hill | rg "Requesting"
   ```
   Required:
   - `/lib64/ld-linux-x86-64.so.2`
   Block vendoring if interpreter is `/home/linuxbrew/.linuxbrew/lib/ld.so`.

## Vendoring (wepppy)

5. Copy binaries with explicit names:
   ```bash
   install -m 0755 /workdir/wepp-forest/src/wepp /workdir/wepppy/wepp_runner/bin/wepp_<tag>
   install -m 0755 /workdir/wepp-forest/src/wepp_hill /workdir/wepppy/wepp_runner/bin/wepp_<tag>_hill
   ```
6. Run provenance + smoke + targeted tests in `wepppy`.
7. Run container smoke checks when `weppcloud` is running.

## Documentation and Release Notes (Required)

8. **Update `/workdir/wepp-forest/change-log.md` (required step).**
9. Add a new top row in the cmark-gfm table with:
   - date,
   - version/commit,
   - concise change summary.
10. Keep table order descending by date.
11. If output/pass format changed, note downstream compatibility impact.

For notable releases, author a self-contained scientific/engineering report
under `docs/release-notes/wepp_<tag>/` following the
[release-note guide](release-notes/AUTHORING.md). Reconcile all shipped changes,
explicitly allow detailed legacy-code descriptions and original code we author,
and complete source/asset disclosure review before PDF publication. Vendor
only the approved PDF and public provenance manifest to WEPPpy. A binary
release does not override the restriction on public legacy source distribution.

## Commit/Handoff

12. Commit changes with release-focused message.
13. Include evidence of build/test commands in handoff note.
14. Push branch and call out any skipped checks explicitly.
