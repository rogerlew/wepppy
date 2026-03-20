# WEPP Binary Rebuild And Vendoring (`260319`)

This note defines the canonical workflow for rebuilding WEPP binaries from
`wepp-forest`, vendoring them into `wepppy`, and validating provenance plus
fixture behavior.

## Prerequisites

- `wepp-forest` checkout at `/workdir/wepp-forest`
- `wepppy` checkout at `/workdir/wepppy`
- pinned compiler available at `/usr/bin/gfortran` (default)
- fixture inputs present at `/wc1/runs/du/dumbfounded-patentee/wepp/runs`

Optional:
- running `weppcloud` container visible in `docker ps`

## One-command rebuild + vendor + validation

From `/workdir/wepppy`:

```bash
tools/rebuild_vendor_wepp_260319.sh
```

The script performs, in order:

1. `wepp-forest/tools/build_wepp_260319_pinned.sh`
2. copy artifacts to:
   - `wepp_runner/bin/wepp_260319`
   - `wepp_runner/bin/wepp_260319_hill`
3. provenance checks (`tools/check_wepp_binary_provenance.sh`)
4. host fixture smoke checks (`tools/smoke_wepp_binary_host.sh`)
5. container fixture smoke checks (`tools/smoke_wepp_binary_in_container.sh`) only when
   the target container is visible in `docker ps`

## Validation behavior

### Host validation (always runs)

- Runs directly on the host (outside containers)
- Uses fixture cases `p962,p1`
- Requires:
  - return code `0`
  - `WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY` in stdout
  - `SIMULATION YEAR = 17` reached

### Container validation (conditional)

- Default container name: `weppcloud`
- Skipped (non-fatal) when container is not visible in `docker ps`
- Same fixture and pass criteria as host validation

## Useful overrides

```bash
# use a different compiler path
COMPILER=/usr/local/bin/gfortran tools/rebuild_vendor_wepp_260319.sh

# target a different running container name
CONTAINER=weppcloud-dev tools/rebuild_vendor_wepp_260319.sh

# run host smoke on a specific binary directly
RUNS_DIR=/wc1/runs/du/dumbfounded-patentee/wepp/runs \
  tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260319
```
