# Decision proposal: approving a freshly built deployment candidate

Status: retained-candidate resume selected by Roger on 2026-11-13 through the
direction to proceed with the remaining Docker Compose deployment work. The
selection authorizes implementation and validation of this workflow, not a
generic skip-build bypass or activation without the ratified evidence gate.
Independent correctness review identified the boundary in the existing
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

## Selected option: explicit retained-candidate resume

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
approval and image-identity substitution. Roger selected retained-candidate
resume when directing the remaining production Compose deployment work to
proceed on 2026-11-13, after clarifying that `wepp.cloud` uses host-local Compose
while `open-wepp.org` consumes registry-published images. Implement this contract
behind an independent checkpoint, then re-review the exact implementation before
production use. The selection does not itself approve a specific image,
exception record, or service interruption.
