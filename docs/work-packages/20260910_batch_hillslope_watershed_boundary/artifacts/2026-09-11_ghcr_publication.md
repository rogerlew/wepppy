# Immutable closeout publication

**Publication verified: success**, 2026-09-11 06:14:22 UTC. The workflow
head SHA exactly matches the recorded closeout source.

- Closeout source: `30a5d0505d9968d412673c3b7290dc7cfb48821a`.
- Immutable tag: `ghcr.io/rogerlew/wepppy:sha-30a5d0505d9968d412673c3b7290dc7cfb48821a`.
- Workflow: [Publish WEPPcloud common runtime image, run 34568456675](https://github.com/rogerlew/wepppy/actions/runs/34568456675).
- Workflow definition: `.github/workflows/publish-weppcloud-image.yml`.
- Platform: `linux/amd64`; Dockerfile: `docker/Dockerfile`.
- Digest: `sha256:43a3a02eec68f0e464bb0af43843a79dc3452b054b5e3d7ff153ffeab41a688e`.
- Immutable reference: `ghcr.io/rogerlew/wepppy@sha256:43a3a02eec68f0e464bb0af43843a79dc3452b054b5e3d7ff153ffeab41a688e`.
- Workflow status/conclusion: `completed` / `success`; job ran
  06:06:38–06:14:22 UTC.
- LFS: both source checks verified **639 tracked Git LFS files materialized**;
  `git lfs fsck` reported **OK**. The image build/push, digest-report step and
  workflow cleanup all succeeded.

The tested/deployed implementation ancestor is
`0a1e2e1efdd816243883254cd99412b022983cd2`. The closeout source differs only in
documentation and retained acceptance evidence; application, test, Docker and
workflow paths have no diff. Forest runs the committed source through its
existing bind-mounted Compose worker service. This publication is not a
registry-based Forest deployment or an openwepp.org rollout.

This post-build publication receipt is committed separately because the image
digest does not exist until the immutable closeout build finishes. Its later
documentation commit does not redefine the recorded closeout image coordinates.
The subsequent openwepp.org rollout must use the immutable digest recorded here
and independently validate scientific output and memory headroom.
