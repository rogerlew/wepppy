# Final pair consumer binding v3

Prepared correction only; no build, model, promotion, or actual final-pair identity is claimed.

The frozen v2 validator rejects any tracked change under `src`, including intentionally promoted `src/wepp` and `src/wepp_hill`. V3 permits only those two exact paths in that cleanliness check. Every other tracked change under `src`, `fpm-src`, `tests`, and `tools` remains rejected, as do untracked inputs in those scopes. The existing committed-source, sidecar, binary-copy SHA-256, and runtime-library checks remain unchanged and mandatory.

Six additive consumers import v3: `run_disturbed_renewal_v3.py`, `validate_release_r5_renewal_v3.py`, `run_roads_final_renewal_v3.py`, `bind_final_application_v3.py`, `run_legacy_frost_renewal_v4.py`, and `run_final_medium_renewal_v3.py`. The legacy runner's helper inventory also names itself and the new validator. Other consumer bytes, including unused historical default output roots and final-pair v2 roots, are preserved mechanically. The producer and its unchanged sidecar validator are untouched. Frozen older consumers remain historical evidence.

Twenty-three controls use a real temporary Git repository. Frozen v2 reproduces the promoted-binary rejection; v3 accepts correctly bound staged and unstaged promoted binaries. Controls reject each promoted binary's hash mismatch; staged, unstaged, and untracked source/control changes in all four scopes; an extra binary-like pathname; a rename; release-copy drift; runtime identity drift; and a mismatched sidecar source. `/usr/bin/true` supplies copied executable bytes for hash/`ldd` checks and is never executed. No WEPP process or compiler runs.

The exact preparation manifest and retained control output are in `out/rock-water-development-20261101/final-pair-binding-v3-preparation-v1/`. Actual renewed-pair binding awaits its real receipt. Independent review and parent authorization remain required before using these new consumers.
