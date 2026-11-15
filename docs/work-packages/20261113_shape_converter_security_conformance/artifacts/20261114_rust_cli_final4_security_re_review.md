# Rust CLI final-4 security re-review

Date: 2026-11-14

Candidate: `a6be89141c234727bb5d89aa5a4b3c2ec51dc284`

Image:
`sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`

## Verdict

PASS. Critical 0; High 0; Medium 0; Low 0.

The independent security reviewer reproduced the former blockers as closed:

- Three cancellations during a real SIGTERM-ignoring descendant's grace period
  returned canonical `CancelledError` only after leader and child were gone and
  no output remained.
- A full-preset Compose render failure performed label discovery, stop, and
  stopped-state verification, exited nonzero, and never activated a candidate.
- Installed-preset authority, orphan discovery, exit-88 precedence, and
  targeted/read-only scope remained sound.

The exact image runs as UID/GID 10001 and matches its source revision, Python
source, parser binary, and provenance sidecar. Fiona, GDAL, osgeo, and pip are
absent. The scanner inventory remains 0 Critical, 17 unique High, 37 unique
Medium, and 96 total unique IDs with no ID or severity drift. Existing
request-path reachability dispositions, including CVE-2026-91094, remain
accepted. SEC-RUST-01 through SEC-RUST-04 remain closed.

Security accepts the explicit same-container residual. It supports closing
#656 as superseded by removal of the GDAL/Fiona failure class, not as proof of a
second parser sandbox. Production rollout remains separate authorization.
