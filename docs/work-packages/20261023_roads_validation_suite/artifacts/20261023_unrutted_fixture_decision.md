# Unrutted negative and positive fixture decision

The full-upload v2 unrutted run failed at two non-positive upstream landuse OFEs:
roads-seg-000001, source OSUNUM6, Topaz271/272, WEPP61/62. The failed attempt is
retained at `/wc1/runs/ro/roads-validation-oct23-v2-unrutted`; no current receipt
exists. Required fill/buffer fields were explicitly 30 m at 10% each.

Preserve this as negative acceptance evidence. The bounded positive integration
fixture excludes only OSUNUM6, pinning source upload and excluded feature hashes.
It exercises actual controller/accounting/replacement behavior on the remaining
site upload. Report both outcomes and exact counts. Do not claim all-upload
unrutted success or compare its watershed differences as pure design effects.
No production logic/default/schema change; no automatic exclusion/retry algorithm.

Reason: the validation suite should expose valid geometry rejection while also
exercising feasible replacement integration. Rewriting native geometry or masking
failures to make the whole upload pass would invalidate the experiment.
