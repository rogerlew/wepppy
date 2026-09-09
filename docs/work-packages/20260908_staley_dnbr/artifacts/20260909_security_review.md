# Security review — dNBR backend

## Metadata and triage

Reviewer: independent `/root/dnbr_security` agent. Date: 2026-09-09.
Working-tree backend change on master based on `52f056eaa`; implementing agent
records the independent review and re-review findings here. Security impact
high for local raster/XML/file boundaries; no changed HTTP/auth/CSRF/queue/
subprocess or runtime network-acquisition boundary. Dedicated review required.
See [correctness review](20260909_correctness_review.md) for valid-state behavior.

Assumptions: trusted local path selection, immutable inputs and single-writer
publication. This is not approval to pass hostile browser uploads directly to
the backend without the separately required upload containment contract.

## Findings and disposition

SEC-01, medium, resolved: padded compressed TIFF blocks bypassed logical cell
limits. A 4x4 image with an 8192x8192 tile required 67,108,864 decoded cells.
The backend now bounds block cells and bytes before reads. Reviewer confirmed
the proof file fails with resource_limit before pixel decoding; regression
test creates this real TIFF structure.

SEC-02, medium, resolved: 100 MiB XML could allocate multiple GB before structural
validation. Identity VRTs now have a 64 KiB preparse cap. Reviewer independently
patched the parser to fail if called and confirmed oversize input rejection
happens first. The resource-limit regression and canonical contract cover it.

## Surface checks

VRT is parsed and validated without GDAL execution; identity sources must be
explicitly allowlisted. Unsupported programs, remote paths, traversal, DTDs
and unapproved source references fail. HFA spill probes, including a patched
absolute reference, failed confined inside /vsimem; no escape was reproduced.
This is evidence for the tested inputs, not a universal parser-sandbox claim.

Output symlinks/existing directories fail without replacing targets. Independent
writer-failure probe preserved inputs and removed staging/reservation. Successful
GTiff/HFA/identity-VRT inputs preserve legitimate behavior. New resource limits
are operational limits and documented explicitly. No new secrets or outbound
user messages are introduced; source downloads were public read-only requests.

## Verdict and signoff

Pass for local backend. Independent security reviewer re-reviewed both fixes
and reports no remaining medium/high findings. Browser containment and trusted
path-selection assumptions remain explicit scope limits.
