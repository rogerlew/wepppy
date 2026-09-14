# Basin-independent preparation checkpoint

Starting implementation revision: `6b61b0e49`. The owner clarified that this
must be generic beyond `addicted-reservist`, then authorized continuation.
Generic implementation is approved; live network execution and deployment are
not authorized by that clarification.

## Canonical delta and compatibility

Authority: module `docs/production_m3_runtime.md`, section
"Basin-independent preparation requirement", with the specification's existing
runtime-contract reference. Derive original in-basin keys and target DEM extent
per project, not fixed development identifiers. Missing primary inputs allow
fallback-only preparation; malformed present inputs remain errors. Incremental
encoded unique-key lists and final encoded SDA requests each remain within
1 MiB, with no automatic batching or expanded acquisition.

Keep prepared-local runtime delivery. Reusable preparation produces observable
receipts and manifests; complete verified receipts may atomically update the
fixed input manifest under the existing module lock, after project source and
prior-manifest identity checks. Failure preserves the prior valid manifest.
Shared soil builders/caches, offline policies, result schemas and model/terrain
eligibility are unchanged. This corrects a named-basin-only delivery framing;
it is not a new scientific parameterization.

## Reviews and disposition

Independent `source_contract_review` approved after clarifying fallback-only
states and distinguishing implementation authority from network execution.
Independent `source_boundary_review` approved after adding outgoing-request/key
bounds and explicit atomic promotion/preservation rules. Both final reviews
have no unresolved medium/high findings. No reviewer edited files.

## Required implementation evidence

Security impact remains high at source/promotion boundaries. Exercise at least
two independent basins with distinct keys/extents; include primary, fallback,
absence and malformed cases. Reject cross-basin/source-identity reuse. Test
stale/failing promotion and preservation of previous inputs through actual
filesystem boundaries. Preserve requests, source identities and failed receipts.
No live network call occurred while preparing this checkpoint. The separately
developed terrain adapter follows the already-approved `89d673c38` contract;
it is not part of this documentation-only ancestor commit.
