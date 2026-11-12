# Decision proposal: approving a freshly built deployment candidate

Status: proposal on hold after the 2026-11-12 operator direction to prioritize
dependency remediation. No resume workflow is approved or implemented.
This document does not authorize deployment, risk exceptions, or a skip-build
bypass. Independent correctness review identified the boundary in the existing
canonical `scripts/deploy-production.sh` workflow.

## Confirmed conflict

The canonical script always builds selected common services without cache and
rejects `--skip-build` when build services exist. The ratified F6 policy binds
approved evidence and dispositions to the exact resulting image IDs. If the
post-build gate exits while the operator reviews new evidence, rerunning the
script builds another candidate; approval of the previous image cannot transfer
merely because its source or version labels match.

The existing script also waits up to 216,000 seconds for warm shutdown, exceeding
the 24-hour evidence window. Freshness and image identity therefore need checks
at the actual activation boundary, not only after the build. The existing error
trap does not restore stopped common-image services; it handles CAP/controllers
and its owned RQ fence only.

## Recommended option: explicit retained-candidate resume

Add a dedicated resume mode to the canonical deploy script, distinct from generic
`--skip-build`. The initial build/collection may stop before any service stop.
The operator reviews the private candidate evidence and independently records
approved policy/disposition/bundle hashes. Resume accepts a specific retained
build receipt only when source/build inputs, selected service map, immutable
image IDs and current Compose selection still match. Any changed input, missing
image, expired evidence or unapproved disposition rejects resume before stop.
It never relabels an image or turns generic skip-build into an escape hatch.

Freeze selected image IDs and compare running containers against that map after
activation. Recheck authority/freshness before destructive steps and activation
retries; preserve warm-stop semantics and document recovery if a later operational
failure occurs after services have stopped. No policy-bypassing rollback is added.
This remains host-local Compose, with no registry, new daemon, or new privilege.

## Alternative: review within one still-running deploy invocation

Keep the fresh build mandatory and wait before service stops for the operator to
supply the concrete approved evidence hashes. The same invocation then rechecks
and activates the exact candidate. This avoids resume mechanics but holds a
long-running deployment process open during manual review and requires explicit
interruption/timeout/recovery behavior. It changes noninteractive deployment
behavior and still needs the later freshness checks.

## Authority and next step

Root AGENTS requires explicit operator approval for changes to established
workflows. The F6 ratified policy separately prohibits candidate-controlled
approval and image-identity substitution. Neither option is inferred from a
request for generic hardening or from the earlier NFS approval. Select one
concrete workflow before implementing its canonical contract and independent
checkpoint. Producer qualification and advisory review can continue meanwhile.
