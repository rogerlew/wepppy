# Roads U12 disclosure remediation acceptance

**Accepted for the reviewed public research artifact scope.** The eight source
disclosure holds identified in the initial review are resolved in the public
working tree. The restricted originals remain private and reproducible. This is
an independent AI disclosure review, not owner or institutional scientific
approval, release promotion, permission to distribute native source, or a
production deployment decision. No repository edits, model runs, commit, push or
publication were performed by this reviewer.

## Scope and disposition

This addendum supplements `roads-u12-disclosure-review.md` and applies the same
native `docs/release-notes/AUTHORING.md` policy. The current snapshot contains
123 new public files: the previous 119, minus `depend-g1.patch`, plus the private
tool receipt, provenance document, copied initial disclosure review, additional
source-verification JSON and final scientific-acceptance JSON. Seven existing
Python paths were replaced with source-free entrypoints. Earlier release
artifacts and the previously tracked source patch remain outside this review.

- All eight original held files in the native `private-tools` directory match
  their independently recorded pre-remediation SHA256 values exactly. The
  public `depend-g1.patch` path is absent.
- The seven public Python files are identical original entrypoint code. They
  contain no legacy source anchors, patch text, encoded implementation or model
  arithmetic. They require `WEPP_NATIVE_RESEARCH_TOOLS`, resolve the same-named
  private implementation, fail explicitly when missing, and forward execution
  through `runpy`. This closes the disclosure hold without altering historical
  instrumenter identities.
- All nine files in the private execution mirror match their canonical native
  copies and the receipt hashes. The ninth is the original public
  `replay_fraction_arithmetic_u11.py`; its public, canonical-private and mirrored
  bytes agree. Every mirrored file is Git-ignored. Ignored status is a commit
  boundary, not permission to upload the private tree elsewhere.
- The provenance document identifies authorship, date, purpose, relationship to
  native routines and retained evidence, and explicitly distinguishes current
  entrypoint hashes from historical instrumenter hashes. It documents the
  required environment and existing container bind mount. This provides a
  concrete reproduction path without publishing source or introducing a silent
  substitute. The receipt contains paths, hashes and dispositions only.
- The copied initial disclosure review exactly matches this reviewer's original
  `/tmp` report. Its original hold wording describes the pre-remediation
  snapshot; this addendum records resolution rather than rewriting that history.

An independent host check confirmed explicit failure without the environment
variable, successful `param_sign_ablation` import with the private mirror and
public sibling search path, and successful fraction-observer `--help`. These
checks execute no model simulations. The parent separately reports a successful
canonical container import; this addendum does not claim to have rerun that
container check or every instrumenter end to end.

## Scientific evidence integrity and late additions

All **25 files bound by `param-u12-scientific-acceptance.json`** independently
rehash to their recorded identities. These include the final scientific
disposition, both fraction disposition/certificate artifacts and applicability
receipt, the late Cedar/source reviews, original analysis scripts, retained
build/source receipts and gate logs. Thus the final acceptance's bound evidence
remains intact after remediation. This check does not independently reproduce
the numerical conclusions or claim an earlier hash snapshot for files that were
not hashed in the initial disclosure review.

All **46 current JSON files** were parsed and recursively rescanned for embedded
patches, substantive routine bodies and source-bearing compiler diagnostics;
none were found. The additional source receipt lists nine source paths and
hashes without bodies. The final acceptance and Cedar receipts contain numerical
observations, identities, gates and scope limits. The acceptance retains the
unmet Roads magnitude objective, two explained strict fraction flags, bounded
terminal-capacity qualification and lack of a universal closure/calibration
claim. These limitations remain visible; no disclosure remediation requires
editing those frozen scientific statements.

## Frozen review identities

Paths below are relative to the Roads program's `artifacts/` directory unless
otherwise stated. The machine-readable verification records all 123 public
snapshot hashes, private preservation checks, wrapper hashes and the 25 evidence
hash comparisons.

| Artifact | SHA256 |
| --- | --- |
| `private-research-tools.json` | `cd968f171260e91d771abdfdc3e70b8ed981ef67a77cacc46278d37c8d921928` |
| `research-code-provenance.md` | `8ef71f9b47204ee1c1e8a372c9160726b5e4e0e90f2e1a64184856e19ebfcf05` |
| `param-u12-scientific-acceptance.json` | `a08723d4cbced7903e2678a26daa53d64741d9f98d713c1002e9010b31001cbb` |
| `param-u12-scientific-disposition.md` | `4e2b8d5d2a60107670147abde0e792349c0e71e86feaaa11fcbf5d14c440968d` |
| `param-u12-cedar-scientific-review.json` | `31385d3f53da6de0b3cf8c900ccd82ec4ad211833d9d1d3be39db0d8e9f0b1e9` |
| `/tmp/roads-u12-disclosure-remediation-verification.json` | `d214b95baf150aed2f15f1c39547921ef78f869797aded6b3bfc6d45ebe6baea` |

No unresolved disclosure blocker remains in this snapshot. Before any later
public commit, inspect the explicit staged allowlist/diff: include the public
entrypoints and receipts, exclude the private native/mirror implementations and
source-bearing generated trees. New or subsequently changed artifacts need
review of their delta. Scientific/native acceptance, binary promotion, final
public report approval and deployment retain their separate gates.
