# wepp1 Git LFS authentication configuration

Verified 2026-11-06 UTC for `/workdir/wepppy` on wepp1.

The repository-local setting
`lfs.https://github.com/rogerlew/wepppy.git/info/lfs.access=basic` caused the
observed checkout stall by selecting preauthenticated LFS requests. Removing
only that cached setting restores normal public-first authentication negotiation.
Existing credential helpers, TLS checks, client selection and other Git settings
remain unchanged. No credential value was copied into evidence.

## Evidence and repair

Both installed clients (2.3.4 and 3.4.1) timed out after 45 seconds with the
original setting and zero of eleven objects transferred. A one-variable override
using normal negotiation downloaded all eleven objects into an empty cache in
1.582 seconds. After the persistent removal, another empty-cache fetch without
an access override passed in 1.632 seconds. A real `checkout-index` through the
ordinary PATH and Git filters, with a separate empty LFS cache, materialized all
eleven files in 4.631 seconds. Every output matched its committed SHA256 and size;
the access key remained absent and the checkout remained clean.

The protected original `.git/config` is retained under
`/var/tmp/wepppy-production-cutover-20261106/git-config-before-lfs-fix`. Parsed
comparison proves exactly one setting removed and no setting added. The repair
was:

```sh
git -C /workdir/wepppy config --local --unset-all \
  lfs.https://github.com/rogerlew/wepppy.git/info/lfs.access
```

This is a diagnosis-specific repair for this public repository, not a rule to
remove authentication settings from other repositories. LFS normally caches
`access=basic` after an authentication challenge; if the setting reappears and
transfers fail, investigate that new challenge and the effective helper path.
The deeper cause of the preauthenticated-request stall was not established.
Do not disable TLS verification, remove credential helpers, or treat a seeded
cache as proof that network transfers work.

## Interrupted checkout recovery

The interrupted candidate checkout contained only this deployment's changes;
the two earlier Caddy edits were already backed up and present in the candidate.
Only the owned stalled LFS filter was terminated, and both Git processes exited
before the index was touched. Eleven missing content-addressed objects were
copied with SHA256 verification. The owned partial checkout was recovered to
the exact published candidate with smudging disabled, then `git lfs checkout`
materialized the cached data. All 661 candidate LFS paths passed size/hash checks.
No unrelated files, branches, running containers or project data were changed.

Before analogous recovery, prove the clean prestate and ownership of partial
edits. Never remove a live Git index lock or reset unrelated work. Preserve
private configuration/diagnostic evidence and verify actual uncached filters.

Deployment evidence is retained in the
[production cutover package](../work-packages/20261105_production_notifications_catalog_cutover/package.md).
