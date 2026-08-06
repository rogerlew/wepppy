# Dot-Sidecar Compatibility Correctness Review

- **Reviewer**: independent reviewer agent `omni_dotlog_fork_review`
- **Date**: 2026-08-06
- **Disposition**: approved after findings were addressed

The final patch skips all dot-prefixed immediate entries in Omni `scenarios`
and `contrasts` normalization and leaves ordinary unexpected entries fail
closed. The exact `.mulch_15_sbs_map` fixture includes its matching real child.

Earlier identity and TOCTOU findings applied to an abandoned, more complex
implementation and are moot because that machinery was removed. The final
review found the minimal code conformant with the amended broad-dot contract.
The accepted residual is that every dot-prefixed entry type is outside link
inventory; rsync, archive, and privacy behavior are unchanged.
