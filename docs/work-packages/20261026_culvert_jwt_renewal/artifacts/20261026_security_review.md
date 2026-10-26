# Security review: Culvert JWT automatic renewal

## Metadata and verdict

Reviewer: independent `security_reviewer` agent `/root/renewal_contract_security`.
Date: 2026-10-26 UTC. Contract ancestor: `4cd8e9cb1`.

**Gate: PASS.** No unresolved high, medium, or low security findings. The bounded
renewal mechanism is deployed and supported by direct live evidence. This is not
a claim that a complete Culvert model analysis was rerun or that every possible
failure state was tested.

Scope: `scripts/culvert_token_rotation.py`, the two
`scripts/systemd/weppcloud-culvert-token-renew.*` units, the integration
`dev-package/scripts/weppcloud_token.py` helper, its call site in the companion
Culvert application, focused regression tests, and the installed SSH/file/systemd
boundaries. The [live validation record](20261026_live_validation.md) records
the deployment and generated-credential consumer chain. Correctness findings
and valid-state acceptance are a separate review gate.

## Security triage and trust assumptions

Security impact is **high** because this change automates credential issuance,
delivery, replacement, and application consumption. A dedicated review is
required. The existing operator account on each host remains trusted; its
existing Docker/issuance authority is not reduced by the restricted delivery key.
The application retains its existing root container identity and instance mount.
This package neither adds root privileges nor creates a new service principal,
scope, issuer, or Kubernetes dependency.

The signed-token verifier and registered service authorization on wepp1 remain
authoritative. Locally decoded claims are used for structure, identity matching,
and scheduling; a live HTTPS request must authenticate successfully before a
candidate replaces the installed token.

## Findings and disposition

| ID | Severity | Surface | Finding and required action | Disposition |
| --- | --- | --- | --- | --- |
| SEC-01 | Low | Receiver/client input bounds | Stripping a bounded read before checking its raw length could accept a token followed by an oversized whitespace suffix. Check raw length before normalization. | Closed. Both receiver and client now reject the oversized raw input. Independent direct regression exercised synthetic valid-looking JWT plus 17,000 spaces; both rejected it, and the receiver created no token target. |

No risk-acceptance exception is required. The initial LAN-address SSH failure
was repaired by selecting the explicit Tailscale hostname and preserving the
source-address restriction and pinned host key; no control was relaxed.

## Surface checks

- Authentication/authorization: issuance fixes the existing subject, audience,
  class, service group, and submit-only scope. Additional run/unknown claims are
  rejected by the receiver. The real API verifies signature, time, revocation,
  and service authorization before returning missing-payload validation.
- Secret handling: token material travels through captured issuance output and
  SSH stdin. It is absent from argv, receipts, reviewed artifacts, and vetted
  error text. Issuer signing secrets remain on wepp1. Subprocess failures do not
  forward captured stdout/stderr to the journal.
- Network boundary: verification uses a fixed HTTPS destination, standard TLS
  certificate verification, disabled redirects, and disabled environment proxies.
  Redirect-rejection behavior is covered by a direct local HTTP test. SSH selects
  `wepp2.tail305ec9.ts.net`, aliases its pinned host key as `wepp2`, disables
  ambient SSH configuration, and requires strict host-key checking.
- SSH capability: the installed key has `restrict`, source
  `100.127.248.45`, and the exact receiver command. Receiver actions are exact
  `status`/`install` matches, without evaluating the original command as shell
  text. Live unauthorized-command rejection retained the installed token.
- Filesystem: the receiver checks directory ownership/mode and no-follow,
  regular-file, ownership/mode constraints. Temporary files use restrictive
  creation, flush/fsync, atomic replacement, and directory fsync. Previous-token
  recovery storage receives the same protection. Valid and hostile filesystem
  states have direct tests, including symlink/FIFO rejection and replacement
  failure retaining the previous credential.
- Concurrency/subprocess: issuer and receiver file locks serialize normal
  overlapping runs. SSH and subprocess execution use argument lists, bounded
  execution time, and sanitized failure reporting. No queue wiring changes or
  arbitrary remote command surface are introduced.
- Compatibility/noninterference: absent receiver state permits initial
  provisioning; current and expired structurally valid credentials are
  inspectable; malformed installed state fails explicitly. Env-only clients
  retain their existing behavior. A configured missing, unreadable, empty,
  invalid UTF-8, or structurally malformed file fails without using an old
  environment credential. A running worker probe read the new credential after
  replacement and authenticated successfully without a container restart.

## Independent deployed-state verification

Read-only checks by this reviewer confirmed:

- The rotation script on wepp1 and wepp2 matches repository SHA256
  `66ab5675572448c6cd7c69f8193fa70bb9463b6ffcc5c04936f86e6d36c99a53`.
- The deployed client helper matches repository SHA256
  `84109cd6979fe42df8426bb07149856d86cce1d87cd7788d2c4072bb82bdb506`.
- Issuer config directory is operator-owned mode 0700; private delivery key and
  known-hosts file are mode 0600.
- Receiver token directory is operator-owned mode 0700; active and previous
  token files are operator-owned mode 0600.
- The actual authorized-key options match the restricted command/source above.
- The user timer is enabled; the installed daily calendar, persistent setting,
  and 15-minute jitter are restored. No force argument or temporary override
  appears in the installed service/timer output.
- The service reports `Result=success`, `ExecMainStatus=0`, and the timer has a
  next ordinary trigger on 2026-10-27 around 08:00 UTC.
- Both Culvert app containers remain running under the existing deployment.

The live validation record additionally retains service-triggered and
timer-triggered rotation, changed SHA256/jti/expiry, same-process loader
consumption, API acceptance, normal no-op, and malicious-input rejection. Tokens
and private keys were not printed or retained by this review.

## Limits and follow-up

Off-host notifications remain unconfigured pending an operator-selected
destination. Local journal, systemd failure state, and the sanitized last-attempt
record are available; no email/webhook delivery is claimed. Observe the first
ordinary daily trigger and the eventual unforced renewal window. This review
does not certify immunity to compromise of the trusted host/operator account,
full model execution, or exhaustive failure coverage.

Sign-off: independent security reviewer; approve the reviewed bounded mechanism
with the limits above recorded. No production changes were made by this review.

## Post-review validation addendum — Codex, 2026-10-26 UTC

The broad-suite obligation pending at review time is now recorded in [validation summary](20261026_validation_summary.md): 11,786 unique passes and 155 skips across broad/tail segments after a process-local correction for the existing browser-cache path. No runtime code changed after the reviewed/deployed hash. Reviewer verdict and operational limitations above are unchanged.
