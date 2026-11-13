# Decision proposal: approving a freshly built deployment candidate

Status: retained-candidate resume explicitly selected by Roger on 2026-11-13 by
answering “yes” to the concrete build-once, immutable-ID-pinned, independently
reviewed, same-host resume workflow. The selection authorizes implementation and
validation, not a generic skip-build bypass or M5 production activation.
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

Freeze selected image IDs and make them the activation input. The private
candidate directory contains the effective rendered Compose file plus an
override mapping every selected locally built service directly to its approved
`sha256:` ID; activation disables pull and build. It must never resolve the
mutable source tag and only compares running containers afterwards as defense in
depth. Recheck receipt, tag-to-ID drift, approval authority and evidence
freshness before the first service change and again after a warm wait before
every activation attempt.

Warm drain occurs before service stop. The deploy-owned RQ fence prevents new
default/batch dequeue while existing jobs finish in the still-running known-good
containers. Rerun the complete gate after drain; rejection releases the owned
fence and changes no container. Before the first stop, capture a private
known-good rendered config and running container image map. Any later failure
automatically recreates that exact prior map with pull/build disabled, verifies
its running IDs, and releases the fence only after restoration. If restoration
fails, return a distinct recovery error and retain the bounded fence instead of
resuming work into a partial stack.

The receipt binds schema/time, hostname, `/etc/machine-id`, Docker Engine ID,
source cleanliness/revision, lock and deploy-script hashes, installed `wctl`
identity, deploy mode/options, canonical secret-safe Compose projection, selected
service map, frozen IDs and retained activation-file hashes. Candidate and
approval directories live under separate 0700 authorities in the owner-selected
private store; 0600 non-symlink records are atomically published and fsynced.
Resume derives the approval filename from the trusted approval root and receipt
hash, never candidate data, CLI or environment. The approval binds exact evidence
manifest, policy and disposition hashes. No policy-bypassing rollback is added.

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
approval and image-identity substitution. Roger explicitly selected
retained-candidate resume on 2026-11-13 after the reviewer requested a concrete
choice. Implement this contract behind an independent checkpoint, then re-review
the exact implementation before production use. The selection does not itself
approve a specific image, exception record, M5 rollout or service interruption.
