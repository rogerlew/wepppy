# Forest application rollback review

Independent reviewer: notification_forest_rollout_review.

All ten restricted baseline snapshots match `ceeaa5960`; candidate snapshots
match `4cf1432d5`. Backup permissions are appropriate. Application rollback may
be exercised with the new schedule disabled, after candidate browser acceptance
and before final schedule activation. Scheduled execution remains a separate gate.

Restore only manifest files and reactivate through canonical targeted-web.
Retain new modules/assets inert, migration and recipient state. Verify normal
authenticated pages, absent bell and unavailable notification routes; compare
exact recipient read timestamps. Restore candidate files, redeploy and repeat
smoke before enabling scheduling. This is application-activation rollback, not
a full old-revision rollback. Do not swap sources while pytest is running.

The host enable flag and running scheduler value must be captured separately
from source snapshots. The operator approved scheduler-only recreation for
activation/rollback; restart does not refresh container environment.
