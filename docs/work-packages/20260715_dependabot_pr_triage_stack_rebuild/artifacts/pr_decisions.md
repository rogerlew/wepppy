# Dependabot PR Decision Matrix

## Frozen Inventory

- **Repository/base**: `rogerlew/wepppy:master`
- **Inventory time**: 2026-07-15 18:54-19:18 UTC
- **Open Dependabot PRs**: 37
- **GitHub state**: every listed head was `MERGEABLE` / `CLEAN`; only PRs #540
  and #541 published a successful check on the frozen head.
- **Recommended actions**: merge 35, defer 1, close/recreate 1.
- **Owner-authorized actions**: all 35 reviewed merge intents incorporated into
  `master`; 34 PRs report `MERGED`, and auto-superseded #564 is present through
  exact reviewed merge ancestry. PRs #570, recreated #586, and #576 are closed
  with the build/compatibility rationale recorded in GitHub comments.

`Merge` means the update is compatible in the tested aggregate candidate.
`Defer` means a coordinated migration is required. `Close/recreate` means the
PR target is stale and should be replaced by a current coordinated update.

## Decisions

| PR | Surface and requested update | Frozen head SHA | Decision | Evidence and rationale |
| --- | --- | --- | --- | --- |
| [#585](https://github.com/rogerlew/wepppy/pull/585) | Docker `msgpack` 1.1.0 to 1.2.1 | `3e8e71bdd1c9c85c7cf5c1c7f99c7f2042379d27` | Merge | Installed in the rebuilt image; aggregate Python gate exercised serialization consumers. |
| [#584](https://github.com/rogerlew/wepppy/pull/584) | CAO `starlette` 0.49.1 to 1.3.1 | `91a892d5b84a61f582b2dcda516cc97308e2e910` | Merge | CAO lock was regenerated with FastAPI 0.137.1, which supports Starlette 1; 20 CAO tests passed. |
| [#583](https://github.com/rogerlew/wepppy/pull/583) | CAO `python-multipart` 0.0.22 to 0.0.31 | `e454d21cb85fcda3f8d244f59b6db395194039f3` | Merge | Coherent CAO lock install and all 20 service tests passed. |
| [#582](https://github.com/rogerlew/wepppy/pull/582) | Docker `python-multipart` 0.0.22 to 0.0.31 | `302d70587fd7d6c6128086ce4b854754e92c2f23` | Merge | Installed in the rebuilt internet-facing application image; stack health passed. |
| [#581](https://github.com/rogerlew/wepppy/pull/581) | CAO `PyJWT` 2.12.0 to 2.13.0 | `24d0421a17c50106ae84a3d2d9e894b2318a5c59` | Merge | Coherent CAO auth dependency resolution and all 20 service tests passed. |
| [#580](https://github.com/rogerlew/wepppy/pull/580) | UI lab Vite 8 group | `3b137ef9ea0ef6ce7cad5167a7782e2dfe0621f2` | Merge | Major bundler migration was regenerated exactly; lint and the 2,752-module production build passed. |
| [#579](https://github.com/rogerlew/wepppy/pull/579) | Docker `tornado` 6.5.5 to 6.5.6 | `6072811ea59700f679b0b4694c81f50b75801175` | Merge | Patch installed in rebuilt image; service startup and health checks passed. |
| [#578](https://github.com/rogerlew/wepppy/pull/578) | Docker `pyarrow` 16.1.0 to 23.0.1 | `e211da45d1d9101ad1816149328fa85c50e1056e` | Merge | Major update installed in the no-cache image and exercised in the aggregate Python suite. |
| [#576](https://github.com/rogerlew/wepppy/pull/576) | Docker `starlette` 0.49.1 to 1.0.1 | `2b5210d3bde4bef96960ae056ec4b5331f789921` | Close/recreate | Target is stale behind 1.3.1. Regenerate a current Docker FastAPI/Starlette pair instead of merging this old lock intent. |
| [#575](https://github.com/rogerlew/wepppy/pull/575) | CAP `express` and `qs` group | `bf4481a7824b9d69234e1fd7bbd485f1f8f0a5b7` | Merge | `npm ci` installed Express 4.22.2 and qs 6.15.2; CAP syntax/import smoke and rebuilt service startup passed. |
| [#574](https://github.com/rogerlew/wepppy/pull/574) | Docker `idna` 3.7 to 3.15 | `3c2b5463837854dc3c189c65009e7c77a6d724bc` | Merge | Installed in rebuilt image; aggregate HTTP/client tests provide compatibility coverage. |
| [#573](https://github.com/rogerlew/wepppy/pull/573) | CAO `idna` 3.10 to 3.15 | `b26944187badc99802abdb6cf76c85032d2806ef` | Merge | CAO lock/install and all 20 service tests passed. |
| [#572](https://github.com/rogerlew/wepppy/pull/572) | CAO `Authlib` 1.6.9 to 1.6.12 | `b9465abf8a6c12cb6723caf659210a36454f070f` | Merge | Coordinated CAO auth lock and service tests passed. |
| [#571](https://github.com/rogerlew/wepppy/pull/571) | Docker `Authlib` 1.6.9 to 1.6.12 | `34b6650a771741fcbc2d6657ffa365cebd3e4b73` | Merge | Installed in rebuilt image; application startup and aggregate auth tests passed. |
| [#570](https://github.com/rogerlew/wepppy/pull/570) | Docker `GDAL` 3.10.2 to 3.13.0 | `615d9b50e6379fa7f43ca84b3ea5a12a444be0d8` | Defer | No-cache build fails: bindings require libgdal 3.13 but the image provides 3.10.3. Requires base-image/system-library migration. |
| [#569](https://github.com/rogerlew/wepppy/pull/569) | CAO `urllib3` 2.6.3 to 2.7.0 | `92447f897f8b63147242dbb8c5da3635d8bdd66c` | Merge | CAO lock/install and service tests passed. |
| [#568](https://github.com/rogerlew/wepppy/pull/568) | Docker `urllib3` 2.6.3 to 2.7.0 | `740f83b5c74dd5bdb7cffe45d8ec34559e784ca5` | Merge | Installed in rebuilt image; network-facing suite coverage and stack health passed. |
| [#567](https://github.com/rogerlew/wepppy/pull/567) | Docker `Mako` 1.3.9 to 1.3.12 | `045e902f01c290d24a2932845ee94c946dfaec2f` | Merge | Installed in rebuilt image; template/application tests exercised aggregate candidate. |
| [#564](https://github.com/rogerlew/wepppy/pull/564) | Docker `mistune` 3.1.3 to 3.2.1 | `0b24a0cb7cdda5bb48ec7300446758517d8f4d7c` | Merge | Installed in rebuilt image; parser/report paths remained compatible in aggregate gate. |
| [#563](https://github.com/rogerlew/wepppy/pull/563) | UI lab `postcss` 8.5.6 to 8.5.12 | `a3093a973ce00c4e118fed294bc29fec54354f9f` | Merge | Exact lock resolution; UI lab lint and production build passed. |
| [#562](https://github.com/rogerlew/wepppy/pull/562) | Docker `lxml` 5.3.1 to 6.1.0 | `172f956c804d88c1420bca4520fcf56a4f7d0d5d` | Merge | Security-relevant major update installed and parser consumers passed aggregate tests. Prioritize this merge. |
| [#561](https://github.com/rogerlew/wepppy/pull/561) | CAO `python-dotenv` 1.1.1 to 1.2.2 | `36116823b2518c7b3cafa429f7a53226f760ae26` | Merge | CAO lock/install and service tests passed. |
| [#560](https://github.com/rogerlew/wepppy/pull/560) | Docker `python-dotenv` 1.0.1 to 1.2.2 | `85873a647b9e1f02b433a9b628f8c7241e75dc07` | Merge | Installed in rebuilt image; configuration tests and stack startup passed. |
| [#559](https://github.com/rogerlew/wepppy/pull/559) | Docker `nbconvert` 7.17.0 to 7.17.1 | `ab82d7e5693699c20f069eac564b8f4b3ad5acd0` | Merge | Patch installed in rebuilt image; report/notebook dependencies resolved coherently. |
| [#555](https://github.com/rogerlew/wepppy/pull/555) | UI lab `protocol-buffers-schema` 3.6.0 to 3.6.1 | `4954e0dcbf616539cfc95967c4fd69b2e83e06b9` | Merge | Exact lock resolution; clean install, lint, and production build passed. |
| [#552](https://github.com/rogerlew/wepppy/pull/552) | Docker `pytest` 8.4.2 to 9.0.3 | `3758cd883406cff577ec5015ffb3b08711f29269` | Merge | Full 4,954-item suite collected under pytest 9; baseline Flask-stub collection defect reproduces under pytest 8.4.2. |
| [#551](https://github.com/rogerlew/wepppy/pull/551) | CAO dev `pytest` 8.4.2 to 9.0.3 | `94cd74ead57a1aec8af5cab99120130d58e74377` | Merge | All 20 declared CAO service tests passed under pytest 9. |
| [#550](https://github.com/rogerlew/wepppy/pull/550) | Docker `Pillow` 12.1.1 to 12.2.0 | `7327786256c36d8a5f59529cacf654a51563c02e` | Merge | Installed in rebuilt image; image/report consumers exercised by aggregate tests. |
| [#549](https://github.com/rogerlew/wepppy/pull/549) | Docker `cryptography` 46.0.6 to 46.0.7 | `67d3d5a30720044e134681c1ae68c0b83706977c` | Merge | Upstream security fix installed; auth/crypto consumers and application startup passed. Prioritize this merge. |
| [#548](https://github.com/rogerlew/wepppy/pull/548) | CAO `cryptography` 46.0.6 to 46.0.7 | `3e6a5b7991020539ecb10c4e6890db83c8147a91` | Merge | Upstream security fix; CAO lock/install and service tests passed. Prioritize this merge. |
| [#546](https://github.com/rogerlew/wepppy/pull/546) | Docker `dtale` 3.20.0 to 3.22.0 | `15f90113fe8bd8cfb1804af141f3487f5d6c594b` | Merge | Installed in rebuilt image; D-Tale service recreated and started. |
| [#545](https://github.com/rogerlew/wepppy/pull/545) | CAO `FastMCP` 2.14.2 to 3.2.0 | `c034fea2dda8d49c3d30f0f58bfc8ea831f5d2fb` | Merge | Major migration resolved coherently; FastMCP import smoke and all 20 CAO tests passed. |
| [#543](https://github.com/rogerlew/wepppy/pull/543) | CAO `Pygments` 2.19.2 to 2.20.0 | `842ae18c8c8edb19f1837c29f4c399d973741b18` | Merge | CAO lock/install and service tests passed. |
| [#542](https://github.com/rogerlew/wepppy/pull/542) | Docker `Pygments` 2.15.0 to 2.20.0 | `3e6b89174e166b752a2d1cf6552b97aa024baa64` | Merge | Installed in rebuilt image; rendering/report dependencies resolved and tests exercised candidate. |
| [#541](https://github.com/rogerlew/wepppy/pull/541) | Static `picomatch` 2.3.1 to 2.3.2 | `0d19aec635282c33568e9b85aa9a683eb6ca727d` | Merge | GitHub `npm-tests` passed; local clean install, lint, and 629-test gate passed. |
| [#540](https://github.com/rogerlew/wepppy/pull/540) | Static `flatted` 3.3.3 to 3.4.2 | `70f3458e5a3061f6afa507b09f56e9ecfd797162` | Merge | GitHub `npm-tests` passed; local clean install, lint, and 629-test gate passed. |
| [#539](https://github.com/rogerlew/wepppy/pull/539) | CAP `path-to-regexp` 0.1.12 to 0.1.13 | `c416122f35a5b4f997f16a692ebb6576f4abd5c0` | Merge | Exact transitive lock resolution; CAP clean install/import smoke and rebuilt service startup passed. |

## Executed Merge Sequence

1. Merged the security fixes first: #548, #549, and #562.
2. Merged paired Docker/CAO updates together where practical: #571/#572,
   #568/#569, #573/#574, #548/#549, #551/#552, and #582/#583.
3. Merged the remaining compatible intents in ecosystem batches. Shared-lock
   conflicts retained the exact reviewed head as merge ancestry while preserving
   previously merged lock state.
4. #576 remains closed; a future current Docker FastAPI/Starlette pair requires
   a fresh review.
5. #570 and recreated #586 are closed; GDAL 3.13 requires a coordinated
   base-image migration.

## Candidate Composition

The tested detached candidate regenerated the intent of all 35 `Merge` rows at
`cc31c121f`. Lockfiles were produced as coherent current resolutions rather than
cherry-picking mutually overlapping Dependabot locks. It intentionally retained
Docker GDAL 3.10.2 and Starlette 0.49.1 for the two non-merge decisions.

## Final GitHub State

- 34 reviewed PRs report `MERGED`.
- #564 was auto-closed by Dependabot as superseded by #587 during rollout. Its
  exact reviewed head `0b24a0cb7cdda5bb48ec7300446758517d8f4d7c` is a merge
  parent on `master`, which contains the approved Mistune 3.2.1 pin.
- Newly opened #587, #588, and #589 were not substituted because their heads
  were outside the frozen review. Recreated incompatible GDAL #586 was closed
  under the same native-library finding as #570.
- The final merged-primary rebuild, service health checks, focused gates, and
  4,897-pass controlled Python suite are recorded in `validation.md`.
