# SUDI-03 final independent security review

Reviewer: `/root/review_7777_security`. Date: 2026-09-28.

## Verdict

**Approved for the reviewed implementation.** No unresolved security findings,
new broad exception boundaries, or risk acceptances. Broad regression completion
and package closure remain owner gates; this review does not authorize deployment.

## Reviewed changes and evidence

Reviewed the working-tree diff from contract checkpoint `e3a12ba42`, confirmed
that checkpoint is an ancestor of HEAD, and inspected the new fixtures,
focused-test output, live acceptance JSON and live acceptance harness. No runtime
edits were made by this reviewer.

The validator explicitly admits 7777 with eight header fields and ten layer
fields. Shared strict tokenization, native numeric representability, bounded
counts, complete consumption and native increasing-depth checks remain active.
7777 density, conductivity and hydraulic fractions are checked before the
permissive parser runs. The existing three-field restrictive-record validation
still rejects negative values and unsupported flags. No label, path, count or
numeric validation was relaxed for previously accepted formats.

The preserving serializer emits ten fields, excludes inferred avke and per-layer
anisotropy, retains profile anisotropy, and revalidates its output. Changes are
within the existing explicit preservation path. Ordinary serialization, request
transport, auth/CSRF, filesystem containment, metadata publication/locks, source
lifecycle and worker authority boundaries are unchanged. Help text accurately
adds the supported version without adding a new input path.

The focused run reports **205 passed**. Tests include native token differentials,
exact widths, invalid numeric values, native depth rounding, hydraulic bounds,
10/11-layer boundaries, raw source preservation and rejected replacement. Native
tests cover synthetic and exact supplied 7777 files through 32 OFEs, compare
every generated profile against source values except requested modifiers, and
reject NaN/Inf markers in nonempty loss outputs. This provides bounded acceptance
evidence for the native shared-array concern noted in the contract review;
it does not claim arbitrary scientific input certification.

The provided CRLF file and committed fixture have matching SHA-256:
`9ff8feb48350d47330b882d5ebe90076d07ee13d09335d4d12ac62fe6eda2350`.
Live evidence records authenticated upload, finished build, normal single/MOFE
preparation, authenticated unchanged-source download, and successful native
execution at 2 and 12 OFEs under uid 1000/gid 993/umask 022. The harness checks
all prepared OFE values and finite loss artifacts. Archive validation log also
reports preserved source metadata/hash after restore.

## Operational limit

An existing development worker retained older imported code; a fresh worker
retried only the disposable run's failed soil job. The retained evidence labels
that retry. Deploy code to web and workers together and restart workers through
the existing deployment workflow before exposing 7777 admission. No production
deployment or shared worker restart occurred during acceptance.
