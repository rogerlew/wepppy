# Project RQ refactor validation

## Tests and Redis readback

- `wctl run-pytest --profile python -- tests/rq/test_project_rq_mutation_guards.py -q`
  passed 69 tests on the isolated candidate. Worktree receipt
  `bdd0df8015b147f58f13d24c495b982b` records matching source fingerprints.
- The command below passed 17 tests, with zero skips and 22 deselections.
  It ran in a disposable `wctl run` dev container with the candidate
  bind-mounted and both changed runtime modules checked by SHA-256.
  The dev image lacks `comrak`, so the run mounted the existing repository
  pin `comrak-ext==0.2.8` read-only and added it to `PYTHONPATH`.

      /opt/venv/bin/python -m pytest -q -rs tests/rq/test_wbt_controlled_failure_integration.py -k "same_run_policy_trees or retry_splices or completion_receipt_releases or admission or exact_tree or actual_root_rq_retry or policy_apply_failure"

The Redis tests use unique queue and run keys. In the commit-then-disconnect
case, the real Redis transaction persists the build as the run tail, places it
once in the queue, and associates the receipt as its dependent. An identical
retry finds the same two IDs. The intermediate-queue case moves the build
to the real RQ intermediate list and checks reuse there. Other cases verify
forward and reverse dependency checks, fail-closed behavior for mismatched
links and orphaned active jobs, and ordered execution through abstraction.
These tests validate the saved RQ records consumed by the refactored reader.
The full test suite was waived.

## Source and generated graph comparison

The base was `47c061fb71617894bc4ceaa12ea6983b9e89b76a`. An AST comparison
confirmed exact signatures, decorators and bodies for all 63 retained worker
functions and all eight moved helpers, plus exact values for seven metadata
keys. The changed-code exception guard passed with zero net increase.

The checked-in static graph JSON and dependency catalog both report drift on
the base and candidate. Comparing graphs freshly extracted from both trees
showed agreement on all 154 edges, with six updated source line locations.
This refactor leaves the existing catalog drift outside its scope. The
`wctl check-rq-graph` wrapper inspects the mounted development checkout, so
the candidate comparison ran the repository checker directly on the worktree.

The observe-only quality report counted 2,972 to 2,722 source lines in the
worker. Its longest function remains 214 lines. The extracted module has
274 source lines and retains the 153-line validator as a faithful move.

This evidence supports local validation of RQ job state and queue behavior.
