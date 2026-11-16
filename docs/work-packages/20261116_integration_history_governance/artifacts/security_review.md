# Security design review — integration history governance

## Metadata

- Package: `docs/work-packages/20261116_integration_history_governance/`
- Reviewer: delegated `ci_security` agent.
- Observed: 2026-11-16 20:49 UTC.
- Source: `420e31b97e962dd6ea79694efe89f348c27ef83f`, plus read-only GitHub API observations.
- Scope: GitHub enforcement, workflow triggers, baseline trust, publication and
  deployment consumers. This is a design review; no controls were implemented,
  GitHub settings changed, credentials changed, or images published.

## Security triage decision

Security impact is **high**. The future work controls which code may be called
accepted, merged, built, and released, and affects agent and CI authority.
A dedicated implementation security review remains required before closure.

The primary threat is accidental loss or omission of accepted work by an agent
or maintainer. A secondary threat is candidate changes weakening their own
checks. The repository owner and anyone able to change enforcement settings
remain trusted authorities. A repository-local checker is not a containment
boundary against those authorities. Do not claim otherwise without changing
credential ownership and the enforcement trust boundary.

Valid states include legitimate unrelated changes, authorized baseline
replacement, offline local development, delayed CI, concurrent PRs, and emergency
recovery. Offline or failed verification may allow work to continue locally but
must not produce an integrated/closed/release-eligible claim.

## Evidence

Read-only commands returned:

```text
gh api repos/rogerlew/wepppy/branches/master/protection
HTTP 404: Branch not protected

gh api repos/rogerlew/wepppy/rulesets
[]

gh api repos/rogerlew/wepppy --jq '{visibility,owner:.owner.type,allow_merge_commit,allow_squash_merge,allow_rebase_merge,default_branch}'
{"allow_merge_commit":true,"allow_rebase_merge":true,"allow_squash_merge":true,"default_branch":"master","owner":"User","visibility":"public"}
```

These observations establish current settings, not historical settings at the
incident. Existing evidence shows a local history omission followed by a valid
fast-forward push; force-push prevention alone would not catch it.

`.github/forest_workflows/pytest-shape-converter-gates.yml` filters both PR and
master-push execution by changed paths. The generated workflow has the same
filters. Its checks execute candidate code from the repository checkout.
`.github/workflows/AGENTS.md` requires generated workflows to be changed at the
source spec and reserves `ghcr-builder` for trusted publishing workloads.

`.github/workflows/publish-weppcloud-image.yml` runs on every master push and
manual dispatch, grants `packages: write`, and builds/pushes the checkout with
SHA-derived coordinates. It has no `needs` dependency or explicit successful
integration/security-baseline check. Immutable source labeling is useful but
does not establish that accepted work survived. The auxiliary publisher runs
manually and validates its runtime contract before push; that does not prove
integration history either.

`scripts/deploy-production.sh` already fast-forwards fetched source rather than
rebasing it, refuses divergence, and gates shape-converter builds/provenance.
Keep those protections. They are code in the candidate checkout, so they do not
independently prove that an older or weakened checkout retained required policy.

## Scaffold alignment

Read `package.md`, `tracker.md`, and `artifacts/incident_and_consumers.md` after
the scaffold was created. Scope and D1–D5 correctly keep policy adoption, remote
mutations, and implementation decision-gated. The package already recognizes
ancestry-versus-behavior, candidate self-modification, and publication consumers;
those are open implementation requirements, not newly missing scaffold sections.

SEC-01 and SEC-04 describe observed current configuration gaps. SEC-02 describes
a design threat the future checker must address; no existing baseline verifier
or successful bypass was observed. SEC-03 confirms absence of an integration
eligibility gate in the current common publisher; it does not establish a breach
of a previously adopted publication policy or an actual bad deployment. Its
required fix applies when D5 adopts that eligibility contract. The consumer
inventory can retain unknown historical impact while marking the current
publisher wiring as inspected.

## Findings

| ID | Severity | Surface | Finding and required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Remote integration | Current master has no protected merge boundary. Establish an active rule requiring PR integration and a named always-run governance result, block force-push/deletion, and explicitly choose bypass behavior. Verify denied operations with an appropriately scoped test identity before claiming enforcement. | Open; implementation pending |
| SEC-02 | High | Baseline authority | A candidate can change the baseline, checker, and workflow together. A green candidate-supplied check is not independent evidence. Read expected baseline policy from a trusted prior reference; require separately reviewed authorization for baseline retirement or checker changes. Document owner/admin trust and test same-change deletion of both implementation and checks. | Open; implementation pending |
| SEC-03 | High | Publication and release | Automatic common-image publication does not wait for integration governance evidence. Add an exact-source eligibility gate before registry writes, including manual dispatch, and bind evidence to source SHA and image digest. Determine equivalent enforcement for existing deploy entry points; do not create a parallel deployment path. | Open; implementation pending |
| SEC-04 | Medium | Required-check availability | Path-filtered checks cannot serve as universal governance results. Add a unique always-emitted check, explicitly fail closed on missing/canceled/stale evidence, and test docs-only/soils-only changes, unavailable runners, and workflow modification. Keep expensive targeted suites conditional behind a deliberate coverage contract. | Open; implementation pending |

SEC-01 is high because every integration can bypass review and validation today.
SEC-02 is high because silently dropping the security implementation and the
means to detect its loss repeats the incident's practical consequence.
SEC-03 is high because an unchecked source revision can acquire a deployable
registry artifact before its eligibility is established. This is not evidence
that the lost Rust converter was deployed or that the common image contains that
service. SEC-04 is medium independently; it becomes a blocker for enabling a
required check without disrupting legitimate changes.

## Recommended minimum and decision points

1. Require a PR and a unique always-run governance check on master, with force
   updates and deletion disabled. Prefer retaining merge commits for initially
   simple accepted-SHA ancestry receipts. If squash/rebase integration remains
   enabled, define a separate reviewed-source-to-integrated-source mapping and
   validate the integrated artifact; raw source-SHA ancestry cannot be mandatory
   for those methods.
2. Decide the independent human approval policy. One required approval is useful
   only if another authorized reviewer is available. A solo-maintainer policy
   may require PR plus checks with zero required human approvals, but it must
   explicitly record that limitation. Agent reviews under the same account are
   not independent GitHub identities.
3. Decide the bypass actor and procedure. Recommend no routine agent/admin
   bypass; reserve documented owner break-glass, with reason, exact refs, failed
   gates, follow-up verification, and subsequent rule-state readback. If agents
   retain owner credentials, this is an operational policy rather than a hard
   privilege boundary.
4. Decide the baseline trust model. Minimum accidental-loss protection uses a
   protected accepted reference, a base-version policy/checker, reviewed policy
   changes, and readback of enforcement settings. Stronger hostile-writer
   resistance needs independently administered enforcement; do not introduce a
   new service or organization migration without a concrete requirement.
5. Decide whether every published image must be eligible or whether unqualified
   build artifacts may exist with a distinct, non-release status. Recommend
   gating the existing publisher before push for the smallest clear contract.
   Never infer deployment eligibility merely from a SHA tag or completed build.

GitHub documents public-repository support for branch protection/rulesets, so
there is no observed private-plan obstacle here. Required status contexts should
have unique names and, where supported, be bound to their expected app. App
binding alone does not distinguish trusted and candidate-controlled workflows
that both run through GitHub Actions. Admin enforcement must be explicit.
See [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
and [required-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).

## Personal-account ownership and enforcement canary

This is a public repository owned by a user, not an organization. Do not assume
organization-only team ownership, actor restrictions, or centrally administered
required-workflow features. Use only capabilities confirmed by effective API
settings for this repository. Another human collaborator with appropriate review
permissions can supply independent review; another agent using the owner
credential cannot. Requiring one approval before establishing that reviewer
would convert every ordinary contribution into an emergency exception.

For D3, recommend PR-only plus the always-run check as the initial enforceable
minimum, with the approval count explicitly ratified. If zero independent human
approvals is chosen, label the result automated-gate enforcement rather than
independent approval enforcement. Keep the repository owner as the documented
ultimate authority. A separate bot credential is outside this package budget.

After explicit authorization, exercise the proposed policy on a disposable
canary branch with equivalent copied requirements and the actual routine writer
identity. Keep the branch outside publication/deployment triggers. Retain the
rule export and observed denial for direct update, missing/failed check, stale
check SHA, and prohibited force-update/deletion; also retain a successful normal
PR. Simulate the original loss and the later-revert case in disposable Git
fixtures/check inputs rather than pushing broken code to master. Do not create
a public issue or intentionally publish a bad image as a test.

A canary proves the exercised policy and identity, not master targeting. After
approved master activation, read back the effective target/rules/check names
and bypass actors, then retain one legitimate integration receipt. Test denied
publication by running the exact gate with registry mutation disabled; later
observe the authorized successful publisher at the approved SHA. No failing
master update or privileged publisher dispatch is needed merely to scaffold or
review this plan.

## Surface checks and validation required

- Authorization and agent tooling: inspect effective permissions and bypass
  behavior using routine actor credentials; owner credentials are not a valid
  negative test for a separately restricted writer.
- CI and secrets: keep PR checks off `ghcr-builder`, use read-only tokens for
  verification, and never execute candidate code in a privileged base-context
  workflow. Baseline data comparison must treat candidate content as data.
- Input and subprocess boundaries: resolve exact full commit IDs, validate
  repository/ref identity, and avoid shell interpolation of PR-controlled names.
- Concurrency: test remote advancement between check and merge/publication;
  stale evidence must not authorize a different SHA.
- Failure handling: missing refs, shallow history, fetch failure, canceled checks,
  missing artifacts, and denied API access must fail eligibility explicitly.
- Observability: retain policy version, source/target SHAs, check run identity,
  timestamp, and rules readback without credentials; keep receipts reachable
  through normal package/PR navigation.
- Valid state: demonstrate a successful unrelated PR and an authorized baseline
  replacement, as well as rejection of a dropped-baseline candidate.
- Application auth/session/CSRF, NoDb/run trees, and queue wiring: no changes
  proposed here; not exercised by this design review.

## Verdict and sign-off

Design review is complete with **3 high and 1 medium open findings**. All have
specific implementation and validation requirements; no risk acceptance is
implied. Implementation security gate: **not evaluated / HOLD** until controls
are implemented and exercised at the real enforcement boundary. Documentation
lint is the only executable validation appropriate to this review artifact.

Reviewer: `ci_security`, 2026-11-16. Package-owner acknowledgment and final
implementation security sign-off remain pending. No security-policy mutation
is authorized merely by this review.
