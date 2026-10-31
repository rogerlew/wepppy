# NFMS-01 independent validation matrix

Reviewer/test author: `/root/validation_matrix`, 2026-10-31 UTC.
Checkpoint ancestor: `2b998e08d`. This is evidence tracking, not final approval.

| Requirement | Direct regression | Status |
| --- | --- | --- |
| Encode failure | `test_failed_mutation_matrix.py::test_precommit_fault_restores_memory_and_later_save[encode]` | Passed final matrix run |
| Partial temporary write | Same test `[temp_write]`: actual file gets prefix before injected write failure | Passed final matrix run |
| Temporary fsync failure | Same test `[temp_fsync]` | Passed final matrix run |
| Atomic replace failure | Same test `[replace]` | Passed final matrix run |
| Version metadata exception after replacement | `test_postcommit_fault_keeps_committed_generation[version]` | Passed final matrix run |
| Notification exception after replacement | Same test `[notification]` | Passed final matrix run |
| Unlock error after replacement | Same test `[unlock]` | Passed final matrix run |
| Post-dump hook mutates then raises | Same test `[hook]` | Passed final matrix run |
| Explicit intermediate commit | `test_intermediate_commit_followed_by_failure_keeps_that_generation` | Passed final matrix run |
| Cancellation/system exit cleanup | `test_baseexception_signal_restores_state_and_propagates` | KeyboardInterrupt and SystemExit passed final matrix run |
| Missing/corrupt/unreadable recovery | `test_failed_recovery_blocks_held_state_then_explicitly_recovers` | All cases passed final matrix run |
| Redis-outage recovery and subsequent successful save | Same test `[redis]` | First draft exposed orphaned aborted lock; corrected, final case passes |
| Legacy signatures, detached, ignore-lock, readonly | `test_compatible_read_modes_and_failed_mutation` | Passed final matrix run |
| Actual Redis expiry + same-object overlap fence + newer durable writer | `test_real_redis_expired_scope_fences_same_object_and_keeps_newer_writer` | Passed final matrix run against disposable real Redis |
| Non-owner explicit recovery cannot poison active owner | `test_explicit_recovery_cannot_quarantine_another_threads_live_owner` | Added after source audit; passed final matrix run |
| Reader cannot install over owner acquired during hydration | `test_hydration_install_cannot_overwrite_newly_acquired_owner` | Added after source audit; passed final matrix run |
| Active replacement owner remains untouched after old owner fails | `test_real_redis_lost_owner_cannot_release_or_restore_active_replacement` | Passed final matrix run against real Redis |
| Orphaned aborted token recoverable by later request thread | `test_later_request_thread_recovers_orphaned_abort_lock_after_redis_outage` | Passed final matrix run |
| Secondary cancellation during recovery/cleanup | `test_secondary_cancellation_propagates_with_primary_context` | KeyboardInterrupt/SystemExit propagate with primary cause; passed |
| Failed live identity mutation restores original path/key | `test_failed_live_identity_change_recovers_original_file_and_releases_original_key` | Passed final matrix run |
| Durable identity mismatch quarantines until corrected | `test_recovery_rejects_durable_identity_change_then_recovers_original` | Passed final matrix run |
| Delayed hydrate cannot erase later quarantine | `test_delayed_hydration_cannot_clear_a_later_failed_recovery` | Passed final matrix run |
| Recovery cancellation plus unlock error preserves signal | `test_recovery_unlock_error_does_not_mask_recovery_cancellation` | KeyboardInterrupt/SystemExit passed final run |
| Direct deletion blocked during quarantine | `test_quarantined_state_rejects_direct_attribute_deletion` | Passed final run |
| First-create failure, optional absence and fresh initialization | `test_failed_first_create_allows_optional_absence_and_fresh_initialization` | Passed final run |
| Declared transient cache rebuilt from durable inputs | `test_failed_mutation_rebuilds_declared_transient_cache_from_durable_inputs` | Passed final run through real decoding/post-load hook |
| Concurrent explicit recoveries cannot replace local token after expiry | `test_concurrent_explicit_recovery_cannot_replace_first_recoverers_token` | Passed final run |
| High-level stale-write error refreshes newer generation | `test_high_level_stale_write_rejection_recovers_newer_durable_generation` | Passed final run |
| Real Wepp/Soils preparation consequence and option aliases | `test_failed_mutation_consumers.py` | Owned by `/root/wepp_repair` |
| Grouped compensation and durable-state restoration | `test_wepp_grouped_mutation_recovery.py` | Owned by `/root/grouped_repair` |
| Manual Batch/derived/source/migration paths | Consumer-specific tests | Owned by `/root/manual_repair` |
| Basic context/decorator/new/deleted/nested/default/initialization | Shared base author coverage | Owned by `/root/base_repair` |
| Parent-fsync warning, cache/metadata best effort, direct dump retry | Existing base boundary characterization suite | Re-run required against final implementation |

All added matrix cases execute real NoDb serialization, file replacement, hydration
and held references; only the named fault boundary and unrelated Redis stub are
injected. Actual coordination uses the existing lifecycle fixture's isolated
Redis server with unique `nfms-<uuid>` run identity and targeted key cleanup. No
flush or unrelated lock/cache mutation is performed. The hydration race test
pauses after real hydration; it does not replace hydration with a synthetic object.

First run: `wctl run-pytest tests/nodb/test_failed_mutation_matrix.py --maxfail=1 -q`
reported 14 passed, one failed, 2 warnings in 10.80 seconds. The failure exposed
a real cleanup defect in the first base draft. Subsequent source review identified
two owner-noninterference gaps and added controlled threaded regressions. Final run after fixes:

    wctl exec -e RQ212_TEST_REDIS_SOCKET=/workdir/wepppy/.pytest_cache/nfms-validation/redis.sock weppcloud bash -lc 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/pytest tests/nodb/test_failed_mutation_matrix.py -q --maxfail=1'

Result: **36 passed, 2 warnings in 11.69 seconds**, zero skips. Existing pytz and
pyparsing deprecation warnings only. Two Redis cases also passed separately
before final expansion (2 passed, 21 deselected, 10.09 seconds). Intermediate expanded runs of 32 and 35 cases also passed before the final
stale-write case was added. Parent owns the shared disposable Redis server lifetime; this agent deletes only its unique
run's key/hash and does not stop the server.

This report is coverage evidence by a test author, not independent final code
approval or full-suite sign-off. Remaining consumer-specific/base/gate evidence
must be consolidated by the primary agent.
