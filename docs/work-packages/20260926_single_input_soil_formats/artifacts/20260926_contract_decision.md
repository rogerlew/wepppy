# SUDI-02 contract checkpoint

Starting revision: `64dc33a0d`. Intended behavior expansion, not a conformance
fix. Operator approval: "we should allow 2006, 2006.2, and 9002 soil formats"
then "make it so" after discussion of raw stacking and WSU serialization.
Existing instruction to commit and execute remains applicable.

Normative delta: expand soil versions alongside 7778; validate their exact
records, preserve avke and 9002 hydraulic values; keep compatible modifiers,
source immutability, native format behavior and ordinary/Disturbed defaults.
Canonical amendments: single-user-defined-inputs-contract.md and ADR-0075.
Applicable unchanged contracts: NoDb persistence/concurrency, rq-response, CSRF,
wepp-run-input, MOFE management artifacts, artifact observability/generated
validation. No auth, queue, management format, binary or transport changes.

Compatibility/data plan and complete state coverage live in the active plan.
Absent and empty sources, valid legacy 7778, new populated versions, reuse,
invalid replacement, missing populated bytes, source archive/restore and
working/failed/completed states retain the current lifecycle. Format-specific
malformed records return existing invalid_single_input errors before mutation.
Native reader certification requires exact generated values and execution at
1/2/12/32 OFEs. Filesystem publication/reuse checks must include new formats.

Security impact: high; expanded upload parsing. Require finite/representable
values, strict field counts, native count bounds, no referenced paths and no
new dependency. Existing bounded upload/auth/CSRF/publication safeguards remain.
Independent correctness and security reviews approved the amended checkpoint;
see adjacent contract_correctness and contract_security artifacts. Their medium
findings are resolved in the canonical contract (native token/comment handling,
developed-label kslast policy and exact-depth clipping). Owner disposition:
implement all required regressions and retain separate final reviews. No open
medium/high design findings; runtime edits have not begun.
