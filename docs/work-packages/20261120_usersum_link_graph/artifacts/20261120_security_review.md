# Usersum snapshot security review

The independent reviewer identified risks involving destination symlinks,
copying a restricted original under a self-vendor path, route variants,
temporary snapshot paths, and malicious Git tree names. Vendor sync
validates disjoint destination directories, rejects destination symlinks,
and reads regular blobs from resolved Git commits. It excludes registered
originals from self-vendor copies. Runtime applies the original role on
detail, raw, source, navigation and search paths and denies access to
temporary snapshot files. Both Git tree selection and destination staging
are covered by the containment checks.

The reviewer confirmed closure of the medium findings. Five independent
focused tests passed. The final isolated suite directly exercised a real
source repository, working-tree-only files, source and destination
symlinks, restricted copied paths, both search and page routes, and
scratch-directory source and raw requests. The final worktree receipt is
`.wctl-test-runs/3ff0b025dc9848b2882d385014d0c99a/receipt.json`.

PostgreSQL search totals are produced before per-result role filtering.
A synthetic stale registration could affect the aggregate total, while
matching protected document content is filtered before display.
