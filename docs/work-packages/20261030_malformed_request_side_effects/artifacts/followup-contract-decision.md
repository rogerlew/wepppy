# Follow-on bounded-field checkpoint

Status: two independent reviews approved; operator authorized this exact documentation checkpoint.
Exact canonical blob reviewed: `b2be0cbb021c31f38b89651b4e5c83f0349b04e9`.

The first checkpoint's numeric section explicitly limits new rejection to named
fields. Consumer review confirmed additional invalid-to-default/late-write paths:
Ash active-mode non-finite values/date, WATAR configured concentration/reservoir
fields, agent chat TTL and nested batch task booleans. The four new rows in
`docs/schemas/request-payload-contract.md` enumerate exact fields, omissions,
null/blank/zero/native-boolean semantics and ignored keys. No scientific ranges,
formulas, authentication or runtime defaults change.

Both independent reviewers (`flask_contract_review`, `rq_contract_review`)
approved the exact revised rows after requiring active-mode field names,
configured contaminant-key scope, literal empty-string TTL handling, container
rejection and existing batch-mapping membership. Canonical doc lint passes.

The corresponding source portions were set aside in
`/tmp/mrs-followup-source.json`; restore them only after the approved amendment is
an ancestor. Other implementation remains under the first checkpoint. This
checkpoint includes only this decision and the canonical four-row amendment;
implementation, tests, unrelated work and other package progress are excluded.

Required authority: the operator prompt explicitly withholds automatic commit
authority; contract-first governance requires an accepted ancestor commit before
implementation. The earlier approval covered checkpoint `3ab204e9c`. This exact
follow-on checkpoint needs explicit commit authority, without authorizing an
implementation commit or deployment.

Execution outcome: the operator explicitly approved this documentation-only commit;
`ca28085ac` is the accepted ancestor. The bounded source changes were restored
and subsequently tested. The authority request above is retained as checkpoint history,
not an outstanding approval requirement.
