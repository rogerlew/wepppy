# wepp_runner/AGENTS.md
> Agent guide for vendoring and maintaining WEPP binaries used by `wepp_runner`.

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`wepp_runner` wraps WEPP executable invocation for hillslope, flowpath, and watershed runs.  
This guide defines the required vendoring workflow for binaries in `wepp_runner/bin`.

## Scope
Applies to:
- `wepp_runner/wepp_runner.py`
- `wepp_runner/bin/*`
- `wepp_runner/templates/*`

## Binary Naming Contract
- Vendor binaries as `wepp_<tag>` and `wepp_<tag>_hill` (example: `wepp_260324`).
- Do not rename or remove existing historical binaries unless explicitly requested.
- Keep `wepp` / `latest` behavior stable unless the task explicitly requires changing defaults.

## Required Quality Gate Before Vendoring (Must)
Before copying any new binary into `wepp_runner/bin`, manual tests in `/workdir/wepp-forest` must pass.

From `/workdir/wepp-forest/src`:
```bash
make clean
make all
```

From `/workdir/wepp-forest`:
```bash
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill
pytest
```

If any command fails, do not vendor.

## Vendoring Procedure
From `/workdir/wepppy`:
```bash
install -m 0755 /workdir/wepp-forest/src/wepp wepp_runner/bin/wepp_<tag>
install -m 0755 /workdir/wepp-forest/src/wepp_hill wepp_runner/bin/wepp_<tag>_hill
```

## Post-Vendor Validation (Must)
From `/workdir/wepppy`:
```bash
tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_<tag> wepp_runner/bin/wepp_<tag>_hill
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>_hill
pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py
```

Optional when container is running:
```bash
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_<tag>
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_<tag>_hill
```

## Implementation Notes
- `wepp_runner.wepp_runner.get_linux_wepp_bin_opts()` auto-discovers `wepp_*` files in `wepp_runner/bin`.
- `_hill` variants are invoked automatically for hillslope/flowpath runs when present.
- Prefer explicit failures to silent fallback behavior in binary selection and process execution paths.
