# Preliminary source proposal reviews

Date: 2026-09-14. Two independent read-only agent reviews were requested under
milestone 1. These review the source inventory/proposal, not a complete canonical
checkpoint. Neither reviewer granted checkpoint or final implementation approval.

## Correctness review

Reviewer: `source_contract_review` (reviewer role). No arithmetic error found
in the weighting examples or 8,705 / 4,311,420 strict support calculation.

Medium: a fresh SDA version cannot establish cached-row vintage. Disposition:
proposal/ADR now distinguish current association from historical version unknown,
and require retained cache metadata/content identities. Source eligibility remains
an open checkpoint decision.

Medium: measured-zero eligibility unspecified. Disposition: proposal explicitly
keeps R-only primary components nonsoil, triggering fallback; finite zero THICK
is eligible, negative sentinel is unavailable. Added examples. This is proposed
policy awaiting owner ratification, not an accepted correction to runtime.

The reviewer also required disclosure that THICK has no equivalent explicit
bedrock filter. Added source-specific material caveat. Authentic candidate-effect,
WEPP parity, paired/overfull cases and S09 evidence remain outstanding.

## Source-boundary review

Reviewer: `source_boundary_review` (security_reviewer role).

Medium: cached provenance conflated with present-day lookup. Disposition as above;
no claim of verified historical survey version will follow merely from SDA.

Medium: object consistency recorded but not enforced. Disposition: proposal now
requires conditional requests pinned to ETag, explicit drift/range/redirect
failure, named SDA endpoint, 30-second request / 120-second THICK overall
deadlines, no retries, and aggregate response-body bounds including auxiliary
reads. These controls must be proven before acquisition; none is implemented.

Low: SQLite read-only and reproducibility claims need qualification. Disposition:
inventory names the exact cache, transaction/query/serialization recipe and
acknowledges unmeasured WAL/SHM noninterference. A full schema/row snapshot with
SQLite identity and isolated source-write tests remains required by S09.

## Gate disposition

The proposal was amended for all reported documentation gaps. Remaining evidence
and scientific/source choices are explicitly open; these reviews cannot replace
the plan's two independent final contract reviews after S05–S09 are resolved.
No approved standalone checkpoint commit exists.
