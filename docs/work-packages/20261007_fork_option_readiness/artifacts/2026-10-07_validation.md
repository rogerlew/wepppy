# FORK-UI-01 Validation Evidence

Date: 2026-10-07 UTC. Checkpoint: `b80235d8f`.
Full-suite completion and final record: 2026-10-08 00:05 UTC.

## Direct regression and local checks

- The new absent-controller readiness test failed before the production patch.
- Final focused Python route/render tests: 118 passed, 189 deselected.
- Frontend: 113 suites / 924 tests passed; lint passed.
- Changed broad-exception enforcement passed (zero new broad catches).
- Controller bundle rebuilt through `wctl run-python`; no generated diff.
- Follow-up metadata directory and descriptor-cleanup checks pass, as does
  combined disabled-control plus restored-job reconciliation coverage.
- Full Python suite: 10,418 passed, 126 skipped in 2,731.84 seconds.
  This run began before the final descriptor-cleanup adjustment and two
  metadata-directory cases; the final 118-test focused run and repeated
  frontend gate cover those follow-ups.
- Observe-only quality tool ran; radon was unavailable and its commit-based
  changed-file report omitted the uncommitted patch. Generated repository-wide
  reports were restored to their clean baseline; no dependency was installed.

## Read-only wepp1 replay

Host: `wepp1`; container: `docker-weppcloud-1`; uid 1002, gid 130.
The candidate helper functions were streamed to Python over SSH and evaluated
in memory. No source installation, server reload, job submission, or project
repair occurred. Compare against the helper extracted from the deployed file.

| Destination | Deployed ready | Candidate ready | Source SBS/Omni available |
| --- | --- | --- | --- |
| `mdobre-coiled-rifleman` | false | true | `[False, False]` |
| `mdobre-smoke-free-trefoil` | false | true | `[True, False]` |
| `mdobre-solvent-courtier` | false | true | `[False, False]` |

All three RQ jobs still report finished with flags `(false, true, true)`.
Each parsed core controller identifies the exact destination directory.
Core file hashes before and after evaluation are identical. These checks
validate readiness eligibility and destination identity, not model outputs.

### Core SHA-256 readback

`mdobre-coiled-rifleman`:

- `ron.nodb`: `b7dc0a72959e64fb720d5ad7e2a61a99a9e120809f71a3a171dc6618432eef46`
- `wepp.nodb`: `a5808ec925e5b8318417865ab713378a8cf3381ced1898b7e3035639e892a08f`
- `landuse.nodb`: `e466ee069764e4ac0fa23fc8ca4822f1e43186cfb48dd3b73dd204e7bbbb4bb9`
- `soils.nodb`: `7c340fa1a48c11ba3be3af302f440778cecbc80014cb12a1236f0b6fd8e4b08d`

`mdobre-smoke-free-trefoil`:

- `ron.nodb`: `030d4429c5678f59490861b103c20fcb6e90c2281f06662f62a0c15e9a203c43`
- `wepp.nodb`: `49066a192c9fe1212642ff89d4748093530e4768cde641a634ba09912dd35a08`
- `landuse.nodb`: `c859e6f829e1ee82d31371d3617d05fd054c8a4621a7a53b6ca4437300f818db`
- `soils.nodb`: `1889ee841f43ab3d94d1e14ca1edcb0b08ecbefe089691947c9af5334e22b47b`

`mdobre-solvent-courtier`:

- `ron.nodb`: `0de5370cfc46564594023b99c70056ad60f56328eb4d11ce8922678ecd2430d3`
- `wepp.nodb`: `e4aebd9a50e58a7c8480d2e32cb1652baa3c7996daef6bc8e04d98fdce600a73`
- `landuse.nodb`: `f6dfe5e32e6cd04b309a6016f7336183244175ea19fb983514ff9f8f6d037ded`
- `soils.nodb`: `2aa81e4897f7ce21148253b7d4408dfc17e2c0dc8877dcab53944a4b3cbf9c4c`

## Remaining claims

UI behavior is locally tested; production readiness predicate is environment
validated through read-only replay. The web endpoint and page are not deployed.
The end-to-end production UI recovery remains a deployment acceptance step.
