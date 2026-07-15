# Validation Evidence

## Candidate

- **Base**: `cc31c121f` (`origin/master` at package open)
- **Detached worktree**: `/home/workdir/wepppy-dependabot-candidate`
- **Composition**: regenerated current lock/manifests for all 35 `Merge`
  recommendations; excluded GDAL #570 and stale Starlette #576.
- **Candidate source edits**: dependency manifests/locks only.
- **Integrity**: `git diff --check` passed.

The worktree and temporary compose override are disposable and are not package
deliverables. GitHub PR state remained read-only.

## Focused Dependency Gates

| Surface | Command/gate | Result |
| --- | --- | --- |
| WEPPcloud static | `npm ci` | Pass; 465 packages installed. |
| WEPPcloud static | `npm run lint` | Pass. |
| WEPPcloud static | `npm test` | Pass; 85 suites and 629 tests. |
| UI lab | `npm ci` | Pass; 365 packages installed. |
| UI lab | `npm run lint --silent` | Pass. |
| UI lab | `npm run build --silent` | Pass with Vite 8.0.16; 2,752 modules transformed. Existing chunk-size and Browserslist-age warnings only. |
| CAP | `npm ci` | Pass; 69 packages installed. |
| CAP | `node --check server.js` plus package imports | Pass with Express 4.22.2 and qs 6.15.2. |
| CAO | `uv sync --locked --all-groups` | Pass; lock accepted without changes. |
| CAO | `uv run pytest test -q` | Pass; 20 tests and 13 existing unknown-marker warnings. |
| CAO | FastMCP import smoke | Pass; `FastMCP` imported under 3.2.0. |

Running bare `uv run pytest` from `services/cao` also collected a repository-level
`services/cao/tests/nodb/test_locks.py` file and failed because the intentionally
isolated CAO environment does not install the root `wepppy` package. The declared
CAO `test/` suite is the applicable service gate and passed.

## Image Build

The first candidate build intentionally included all preliminary updates:

```text
docker compose --env-file /home/workdir/wepppy/docker/.env \
  -f /home/workdir/wepppy-dependabot-candidate/docker/docker-compose.dev.yml \
  build --no-cache weppcloud cap
```

- CAP built successfully and its `npm ci` reported zero vulnerabilities.
- WEPPcloud stopped while building GDAL 3.13.0: the Python bindings require
  libgdal 3.13 or newer, but the base image provides libgdal 3.10.3.
- This is the decisive evidence to defer #570 to a base-image/native-library
  migration.

After restoring only the baseline GDAL pins, the same no-cache WEPPcloud build
passed. It compiled GDAL 3.10.2 and Fiona 1.10.1 from source, installed the full
candidate Python dependency set, and produced image
`sha256:7d35c2aecba43217ce39ee8cbdea25c17d8e2ea2924024a1f3f68c09f9319def`.

## Stack Recreation and Health

RQ default and batch queues were empty and all 10 workers were idle before the
restart. The complete development stack was recreated with the candidate
compose file. A temporary override referenced existing local secrets by absolute
path and mounted the primary checkout's ignored disturbed-matrix test fixture
read-only; it did not copy or log secret values.

Evidence from the running stack:

- `/workdir/wepppy` in `weppcloud` resolves to the detached candidate.
- Status and preflight `/health` endpoints both returned `OK`.
- WEPPpyo3 imported from
  `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py`.
- Installed candidate versions included cryptography 46.0.7, lxml 6.1.0,
  PyArrow 23.0.1, pytest 9.0.3, python-multipart 0.0.31, and GDAL 3.10.2.
- CAP reported Express 4.22.2 and qs 6.15.2.

## Full Python Gate

The canonical command was executed first:

```text
wctl run-pytest tests --maxfail=1
```

It stopped during collection because
`tests/climates/daymet/test_daymet_singlelocation_client.py` installs a
synthetic `flask` module when Flask has not already been imported, but the stub
does not define `Request`. Application code then fails at
`from flask import Request`. The same collection error reproduced after
temporarily substituting baseline pytest 8.4.2 in the disposable container, so
this is not a pytest 9 regression.

For dependency assessment, the full suite was rerun under pytest 9 by importing
the installed Flask package before calling `pytest.main()`. The first diagnostic
run reached 1,523 passes before an untracked/gitignored fixture was absent from
the detached worktree. The primary checkout fixture was then mounted read-only
and the complete diagnostic run restarted without modifying candidate source.

The complete diagnostic run finished with 4,888 passed, 58 skipped, and 9
failures in 539.13 seconds. Every failure was in one of two generator files and
reported a missing file under the gitignored
`deductive-futurist/wepp/runs` fixture directory. After mounting that existing
primary-checkout fixture read-only, both complete files passed: 31 passed in
9.89 seconds. Thus all 9 failed cases passed without any dependency or source
change.

## Interpretation

The canonical Python gate is not green because of an existing test-isolation
defect, not because of a candidate dependency. The controlled full-suite run
plus the fixture-complete targeted rerun account for every observed failure and
provide the aggregate compatibility evidence. A focused follow-up should make
the Daymet test import the real Flask package or provide a contract-complete
stub, and should materialize required ignored fixtures for detached worktrees,
so future canonical runs do not depend on collection order or developer-local
files.

## Restored Local Stack

After candidate testing, the complete stack was recreated from the primary
compose file. The running `weppcloud` container now mounts
`/home/workdir/wepppy`, retains candidate image
`sha256:7d35c2aecba43217ce39ee8cbdea25c17d8e2ea2924024a1f3f68c09f9319def`,
passes status and preflight health checks, imports WEPPpyo3 natively, and reports
the tested candidate dependency versions. All 26 long-running compose services
report running; the `preflight-build` and `status-build` one-shot helpers
completed successfully and are exited by design. Post-restore `wctl rq-info
--detail` reports zero queued/executing jobs and all 10 workers idle.

## Merged-Master Rollout

The owner subsequently authorized the 35 reviewed updates. Local `master` was
fast-forwarded to `1c4fd3c50` after the merge sequence. GitHub reports 34 of the
reviewed PRs as `MERGED`; Dependabot auto-closed #564 as superseded while the
rollout was in progress, so its exact reviewed head
`0b24a0cb7cdda5bb48ec7300446758517d8f4d7c` was incorporated as a merge parent.
The resulting Docker manifest retains the reviewed `mistune==3.2.1`. Newly
opened #587-#589 were excluded because they were not part of the frozen review.

Clean merged-manifest gates passed:

- WEPPcloud static: `npm ci`, canonical lint, 85 suites, and 629 tests.
- UI lab: `npm ci`, lint, and Vite 8.0.16 production build with 2,752 modules.
- CAP: `npm ci`, syntax/import smoke with Express 4.22.2, qs 6.15.2, and
  path-to-regexp 0.1.13.
- CAO: locked `uv sync`, FastMCP 3.2.0 import smoke, and 20 tests.

The no-cache merged-master build completed with these images:

- `wepppy-dev`: `sha256:18e7a4a4b09401c0d270bbad55ccedafe62a5a791df59eccd59c56e573dd21c9`
- `wepppy-cap-dev`: `sha256:c6b4a62b98f08959b6dc3558cbbbce9d0f98c8984842ef33faf2101df51c74cb`

The full primary compose stack was force-recreated from those images.
`weppcloud` mounts `/home/workdir/wepppy` at `/workdir/wepppy`; installed
versions include pytest 9.0.3, cryptography 46.0.7, GDAL 3.10.2, Mistune 3.2.1,
Starlette 0.49.1, and urllib3 2.7.0. WEPPpyo3 imports from the native mounted
release at `/workdir/wepppyo3/release/linux/py312/wepppyo3/__init__.py`.
Status and preflight both returned `OK`. Final compose state was 26 running
long-lived services and two build helpers exited 0; RQ reported zero jobs and
all 10 workers idle.

## Merged-Master Python Gate

The canonical merged-primary command again stopped during collection on the
same Daymet synthetic-Flask defect:

```text
wctl run-pytest tests --maxfail=1
ImportError: cannot import name 'Request' from 'flask' (unknown location)
```

No dependency or application source was changed for the diagnostic rerun. The
installed Flask package was imported before invoking `pytest.main(['tests'])`
inside the rebuilt `weppcloud` container. Because the primary checkout contains
its existing ignored fixtures, the complete run finished without the detached
candidate's fixture exceptions:

```text
4897 passed, 58 skipped, 412 warnings in 620.49s (0:10:20)
```

Exit status was 0. This is the final aggregate compatibility result for the
merged dependency set; the canonical wrapper defect remains a test-isolation
follow-up rather than a dependency regression.
