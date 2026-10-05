# Independent Contract Review - UI, Transport, and NoDb

**Reviewer**: `contract_review_ui` (read-only sub-agent)
**Date**: 2026-10-05
**Verdict**: checkpoint blocked pending corrections and exact operator approval

## Findings

- **High - default contradiction**: Modified climate paths generate
  `_cligen_seed` but do not consume it; `par_mod(None)` actually uses
  `-r12345`. Treating legacy/generated integers as explicit would change blank
  output and require a parameterization ADR.
- **High - approval precision**: The original request approves the feature but
  not the exact absent/empty/range/batch/Tenerife/malformed-state matrix required
  for a bounded cross-owner checkpoint.
- **High - batch ambiguity**: Current batch policy excludes `_cligen_seed` as
  per-leaf runtime state, so user configuration needs a distinct persisted
  authority and base-to-leaf rule.
- **Medium - Tenerife visibility**: The draft required universal exposure while
  the existing Advanced options card is hidden for Tenerife.
- **Medium - durable corruption/read-only states**: Malformed persisted state
  and read-only rendering needed explicit behavior and regression evidence.
- **Medium - omission wording**: Omission preserves an existing override; it is
  not equivalent to blank/automatic.
- **Low - lexical form**: Whitespace, leading signs, and leading zeros needed
  exact rules.

No implementation files were edited by the reviewer.
