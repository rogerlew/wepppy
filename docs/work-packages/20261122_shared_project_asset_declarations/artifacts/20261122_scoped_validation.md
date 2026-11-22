# Scoped implementation evidence

The candidate was `f17ec6ca3681efd5f93207a8b825b1059c94c177`. Its baseline was `a957440abbc00b51ddb356e74d84b50382edae3f`. The reviewed contract commit `1b51ac142` is an ancestor. The isolated development runs used the existing Comrak validation image and the candidate checkout. The following wctl receipt IDs identify the runs under `.wctl-test-runs/` in the detached validation worktree.

| Check | Result | Receipt |
| --- | --- | --- |
| Combined producer, migration, declaration, export, query and RQ tests, using a disposable Redis socket | 461 passed, zero skipped | `55e36bd7f98f4222b3657cf6290fa872` |
| Roads project inspection | 6 passed | `3e45b62520dc4187814ac057d18a3b6f` |
| Query and report regressions including HTTP scope and Storm Event Analyzer | 261 passed, overlaps combined suite | `704c1585ed5a463cbcf8b8a7b8ad80c2` |
| Independent security reviewer’s selected boundary checks | 23 passed, overlaps combined suite | `665040566c004fbea5d053c14b22c26b` |

The cross-owner test feeds published Peridot and WEPP outputs through real refresh receipts, catalog publication, typed queries and Feature Export SHA-256 selection. The adapter tests check named parent visibility, inherited/local precedence, equal-schema distinct-value selection, legacy catalog compatibility, and dependency/cache identity. [Cross-owner test](../../../../tests/nodb/test_shared_asset_publication.py) · [Scoped test matrix](../prompts/completed/implementation_execplan.md)

The supported Python 3.12 runtime reports a pathlib deprecation in the hill-loss destination calculation. Before supporting Python 3.14, pass the joined baseline prefix as one argument to `Path.relative_to`.
