# Forest acceptance evidence

Date: 2026-08-26
Host: `forest1`
Candidate: `1bbc0c66da84b823b47bce062e01d123a18766c0`

## Deployment

- The Forest checkout was clean and tracked
  `origin/feature/project-owned-config` at the candidate revision.
- `./scripts/deploy-production.sh` completed twice with no arguments: first
  with every project-config flag false, then with only the reader true.
- Both runs reported healthy WEPPcloud, rq-engine, and CAP endpoints; accepted
  state for every recreated service; candidate-image identity; stable container
  identities/restart counts; registered workers; and a clean RQ fence resume.
- After reader validation, the three writer flags were set in Forest's
  gitignored `docker/.env`. The five consumers were recreated together after
  proving zero active default/batch jobs. Each reported all four flags `true`
  and the HTTP health probes passed.

Tracked Compose defaults remain `false`. Production was not contacted.

## Compatibility and matrix

- `_defaults.cfg` was a regular file; `_defaults.toml` was the relative symlink
  `_defaults.cfg`; both names had identical SHA-256 content and parsed as TOML.
- The focused suite ran inside the deployed `wepppy:latest` environment:
  **148 passed**. Test sources/assets existed only under `/tmp`.
- Coverage includes flattened/legacy readers, manifest degradation, all four
  initial DEM/backend combinations, named presets, builder constraints,
  climate/soil/land-use selections, capabilities, additive updates, RQ/API
  contracts, and builder UI contracts.
- Persistent artifacts live under
  `/wc1/runs/wp11-project-config-acceptance-20260826-b`. Four builder pairs and
  one `disturbed9002` preset materialized and reopened without shared fallback.
  The preset retained SHA-256
  `e138211d6e136973513b0b93d33bc726c664b2fc683e5327b7406b457ed7a0fe`
  through copy, tar archive, restore, and reopen.
- After restarting all five flag consumers, all seven builder/preset/fork/
  restored locations reopened as valid flattened projects.

The sibling path without `-b` is a retained failed probe. It stopped after one
artifact because the probe compared a raw ConfigParser string including TOML
quotes. The corrected probe strips parser quotes; production code was unchanged.

## Rollback

Pre-feature `master` revision `6af9ecdd6` is not writer-safe: it contains only
`_defaults.toml` and no project-config reader. The supported rollback reader is
therefore `cb7698b28`, the first reader-capable feature revision. Code from that
exact Git tree was loaded from `/tmp/wp11-rollback`; its module path was asserted
before it reopened a current builder artifact, named preset, and archive-restored
preset as valid flattened projects.

A full historical-stack redeploy was not performed. The canonical no-argument
deploy pulls the branch tip; an old detached revision would require a
noncanonical `--skip-pull` operation or temporary remote branch. Reader
compatibility—the data-safety condition—is proven. A full service rollback
requires a supported pullable rollback ref.

## Explicit dispositions

- Authenticated browser creation and real queued DEM/climate/soil/land-use
  model preparation were not run because WP11 has no disposable authenticated
  Forest fixture. Resolver/materializer, API/RQ, and persistent-artifact
  evidence passed, but WP12 must not call this a browser/full-model smoke test.
- A full rollback/redeploy cycle remains unclaimed for the reason above.
- These gaps do not enable production. WP12 remains the separate cutover gate.
