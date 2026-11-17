# wepp1 credential staging receipt

**Performed**: 2026-11-17 19:13:48 UTC.  
**Authorization**: Operator requested installation from `/tmp/cilogin_secrets.env` on wepp1 while deferring deployment.

## Procedure and result

Read source keys `CLIENT_ID` and `CLIENT_SECRET` as data, never sourced as shell code. Validated the two nonempty keys locally without printing values. Verified `ssh -o BatchMode=yes wepp1` host identity (`wepp1`), initial directory (`/home/roger`), repository (`/workdir/wepppy`), secret directory mode/owner (`0700 roger:roger`), and Git ignore coverage before writing.

Transferred values over SSH stdin to a Python installer. No credentials entered command arguments, repository files, or output. The installer checked host identity again, rejected symlinks and differing existing values, created each file exclusively, and compared destination bytes to source in memory.

| Destination on wepp1 | Mode | UID:GID | Readback |
| --- | --- | --- | --- |
| `/workdir/wepppy/docker/secrets/oauth_cilogon_client_id` | `0600` | `1002:1003` | source match |
| `/workdir/wepppy/docker/secrets/oauth_cilogon_client_secret` | `0600` | `1002:1003` | source match |

The client ID is staged alongside the secret for a self-contained handoff even though client IDs are not confidential. These files are inactive: no `.env`, Compose manifest, container, or service was changed. This proves host staging only; container readability, registered-client approval, and login have not been tested. Original local source remains in place.

## Recovery and activation boundary

Same-value staging is repeatable. Refuse differing existing values rather than silently rotating credentials. A partial installation can be completed after checking the existing file matches the same source. Before any eventual rotation, document rollback and operator authority. Removing only these staged files would undo staging, but first verify no later rollout has begun consuming them.

Future implementation should consume `oauth_cilogon_client_secret` through `OAUTH_CILOGON_CLIENT_SECRET_FILE=/run/secrets/oauth_cilogon_client_secret`. At separately authorized activation, populate `OAUTH_CILOGON_CLIENT_ID` from its staged file using the existing nonsecret environment convention; do not introduce a second credential loader. Do not copy the production credentials to development. No deployment is authorized by this receipt.
