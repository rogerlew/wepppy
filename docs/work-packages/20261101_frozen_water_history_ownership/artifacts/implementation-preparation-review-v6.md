# Prepared observer v6 implementation review

Disposition: **execution approval withheld.** This is a read-only review of prepared instrumentation; no build or native invocation occurred. The concrete runner and reader are still pending review.

Verified all seven before/after source identities against the pinned build and prepared-v6. All original lines remain in each native routine, with observational calls added and the authored helper appended separately to FRWATC. Added executable lines and the public helper/state/control driver fit the 72-column profile. Native COMMON declarations are not resized. Helper writes are confined to observer bookkeeping and its dedicated trace.

The inserted FRWATC local observations occur after assignments. Native DG-guard jumps to labels 15/40 bypass the added VARDP observations before those labels, avoiding undefined local reads on those paths. The normal main footer is reachable after completion output. Mapping pre/post IDs, actual FROSTN parent IDs, schema/footer counts and per-OFE pending initialization/phase flags provide useful reader context. The reader must track all still-open mappings; last-map helper context alone is not an ownership join. INIT_PRE carries the new initialization-attempt epoch although its values precede initialization, which must be documented in the reader schema.

## Blocking readiness finding

`fh_ready` treats initial-frost kind2 as a complete fine-state initialization whenever NFINE is bounded. That inference is not established by the actual initializer. After its first frozen-layer loop, native FROSTN chooses the next start from a loop index; the subsequent deeper-layer loop reuses jstart rather than resetting it for each layer. Consequently, kind2 alone cannot certify assignments to every active fine cell. A valid count is not proof of initialized content.

Provide explicit coverage/readiness evidence for those cells, or declare and enforce an unsupported-path guard before additional fine-state reads when that initialization path lacks proof. Preserve any resulting failure instead of initializing model fields to satisfy the observer. No-frost kind1 and the fully assigned synthetic kind3 have explicit full coverage. In particular, D0_SUPPORT passes SLSW even when native support is at/below 1 mm and native direction0 would skip that read; its safety depends on the readiness proof. A guard only inside the logging helper cannot prevent argument evaluation at the call site.

No execution PASS follows until this finding is closed and the actual reader/runner are reviewed. Preserve preparation failures and unexecuted revisions as declared.

## Reviewed identities

- `fh_observer.for`: `6a31f748c565fa7419b1635840d98d614bac72c6b50b877d7c77e295768843ad`.
- `fh_state.inc`: `a8b738dcfb0b6797f6d56c5b35dd0e1513a61aaf1f6ebc4365ddbc0888d24cea`.
- `observer_control_driver.for`: `65c94b8a6298151c11d701d20f770fc9f77854d7cdf9a2a3f04ba162c4eb1c0b`.
- Private `prepare_observer_v6.py`: `7e6c90de77a3ea4134cabebc7f010518639fba4106fbb1049d2636c1f42a5ba2`.
- Private `prepared-v6/source-bindings.json`: `081176e8f8ab610a0b31ed572f397e04a8346f57bafd4a8e7523ccfdf15c1cf2`.
- Private `prepared-v6/observer.patch`: `8bc90f6d3944b1436483b8853310e87d1f0b150aa71b4e9a15a92566846a7896`.
