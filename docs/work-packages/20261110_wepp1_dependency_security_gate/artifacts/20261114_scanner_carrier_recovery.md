# Scanner carrier recovery

## Decision

Use the collector's already pinned Node carrier for the hash-pinned Syft and
Grype executables:

`docker.io/library/node:20-alpine@sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb`

The prior scanner carrier was recorded only as local Docker image ID
`sha256:9823645c452a9a994f575ed238e1a4f67365acbf8e842db769060820fab06449`.
It was absent on wepp1, wepp2 and wepp3 after ordinary image pruning, and the
record contains no registry repository digest from which that image can be
recovered. The first final-candidate collection therefore failed closed at
`scanner-image-metadata`; it produced no bundle or approval.

A mutable tag or an attempted reconstruction is rejected. The selected carrier
was already part of the collector's qualified npm boundary, is pullable by an
immutable repository digest, and declares no implicit volume. This change does
not alter the pinned Syft or Grype bytes, versions, configuration, database
policy, evidence schema, evaluator, candidate image, or finding policy.

## Readback

On wepp1, both retained executables ran successfully in the selected carrier as
UID/GID `1002:1002` with a read-only root filesystem, network disabled, all
capabilities dropped, `no-new-privileges`, no Docker socket, and only the exact
executable mounted read-only. Version output remained Syft `1.57.1` with schema
`16.1.13` and Grype `0.121.3` with supported database schema `6`.

The focused collector and channel-template regression selection passes 16 tests.
Fresh end-to-end collection against each final host candidate remains required;
this recovery decision is not evidence approval or rollout authorization.

