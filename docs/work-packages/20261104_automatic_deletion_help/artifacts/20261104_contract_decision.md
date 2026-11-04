# Contract decision

Starting revision: `1ee468e781c959655e95fa674b80a52848c217a1`.

Operator approval: “Disable automatic deletion”; “Automatic deletion is enabled
for [readable date]”; “Automatic deletion is disabled”; “fix it. run scoped
tests. commit and push”. Scope is the assessed deletion/help journey.

Authorities amended: project TTL control contract; Runs catalog TTL deletion
contract; run-catalog projection contract; Usersum specification. Shared
controller and CSRF contracts continue unchanged.

Normative delta: plain-language labels, readable UTC dates, explicit known
status, contextual help, Managing projects navigation, WEPPcloud Help shell,
searchable task-oriented article. Add nullable catalog `ttl_disabled` without
storage changes. Unknown and stale states must not claim deletion is disabled.
Failed checkbox changes restore the confirmed state and retain accurate status;
network failure text directs reload because the server may have saved the change.

Classification: intended presentation/data-projection change; not a retention
policy or access change. Rejected: acronym-only wording, treating no expiration
as proof of disabled deletion, and new storage or services for an existing state.

State matrix: active valid date; disabled; excluded; absent; empty; legacy;
malformed/unreadable; PostgreSQL pending/stale; success and rejected/uncertain
mutation responses. Existing scope/CSRF errors remain errors. Read-only catalog
paths never repair data. Real TTL persistence is already covered by the prior
route repair; new tests trace writer/readers/JSON/DOM and failure restoration.

Two independent read-only reviews and their disposition precede the checkpoint
commit. Implementation conformance is pending. Only scoped tests are authorized.
