# Bundle header freshness checkpoint

Starting revision: `4e000950a` plus uncommitted reviewed post-fire/NoDb waves.
Execution authority: owner's request to execute this package, including confirmed
consumer fixes and checkpoint commits. Consumer: C10 in m1_correctness_inventory.

## Authority and delta

`docs/schemas/file-dependency-freshness-contract.md`, Controller bundle header
identity, ratifies the existing expected-build-ID behavior documented in the
controller README. Shared controller contract and authentication are unchanged.
The concrete defect is a cached old build date after same-size/restored-mtime
replacement, reproduced by the real callable in m1_correctness_probe.json.

Remove the metadata-keyed header-result cache and read the existing 80-line
header on every lookup. Do not hash the entire bundle, change parsing, add a
persistent identity or change unknown-value handling. This creates no run schema
or persisted compatibility transition. Reader rollback only restores the defect.

## State and operation matrix

| State/operation | Required outcome |
| --- | --- |
| Missing, unreadable, empty or no header | Existing None/unknown; no banner caused only by absence |
| Valid current header | Current header date |
| Same-size rewrite with restored mtime | New date immediately on next lookup |
| Hard link, chmod, touch, identical replacement | Same date if readable |
| Atomic replacement while reading | Complete old or new header allowed; next lookup reads current path |
| Existing unusual whitespace/invalid UTF-8 | Existing parser behavior unchanged |

No new containment or access authority is introduced. Every call performs the
existing file open, including warm lookups; stale cache cannot bypass a later
read denial. Baseline real-call reproduction is retained. Add real rewrite and
replacement tests, unknown cases and a warm 1,000-lookup benchmark on the actual
bundle. Budget: mean lookup below 1 ms on the representative local mount.
No frontend code changes are needed; restarted Flask-rendered expected ID is
part of final runtime acceptance. Independent correctness/security checkpoint
reviews and docs-only ancestor commit are required before implementation.
