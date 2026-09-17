# S02 profile SBS security checkpoint

**PASS for the refined bounded design checkpoint.** Actual implementation,
performance and runtime acceptance remain pending. This review covers SBS event identity
section in `PROFILE_TEST_ENGINE_SPEC.md` and `profile_sbs_contract_decision.md`.
Reviewer: `freshness_security`. No production/test changes or runtime probes
were made during QA's exclusive raster timing.

## Finding

**P-S01, medium, closed at draft level below: a new capture failure before creating its
event directory can silently downgrade playback to a historical seed.** The
proposed reader uses event-directory existence to distinguish new evidence
from legacy history. `ProfileAssembler.handle_event` appends the event before
writing the run pointer, ensuring config seeds and invoking capture
(`assembler.py:66`). Any intervening failure, absent run directory, or failed
event-directory creation can therefore leave a new successful SBS response in
history with no event seed. The draft then directs playback to canonical-first
legacy behavior, potentially replaying an earlier upload as the newer event.

Preserve append-before-fallible-copy and old history. Mark newly appended SBS
events as requiring the new capture format, or establish an equally durable
pre-capture association, so missing new evidence fails explicitly even when
directory creation never succeeded. Only genuinely older unmarked events may
use the documented legacy branch. Do not rewrite existing JSONL history or
invent a completed receipt on read. An inability to write any event at all is
different from a successfully appended event followed by capture failure.

## Boundary requirements

The event-ID hash is a path key, not authorization or scientific identity.
The current browser ID contains timestamp/counter values
(`controllers_js/recorder_interceptor.js:475`), and the paired response copies
that ID. Bind the exact event ID in the validated receipt and keep receipt
fields limited to the stated nonsecret provenance. Do not serialize headers,
cookies, JWTs, email or request bodies. Duplicate same-ID delivery must preserve
a completed entry and explicitly reject incompatible evidence rather than
overwrite it or relabel it successful.

Apply confinement to the newly owned `events/<hash>` path and fixed payload,
including symlinked directory/leaf substitutions. A receipt basename check alone
does not confine the open if an intermediate event path escapes. Preserve the
existing seed-root and source-path authority rather than adding a blanket ban
on already supported project roots. Cover failed creation/copy/read access,
partial retained payloads and promotion of failure records.

The existing source selection prioritizes Disturbed, then Baer, then discovered
TIFFs (`assembler.py:292`). A selected source's read or copy failure must not be
silently converted into another file's successful receipt through the current
permissive snapshot helpers. Preserve the intended selection order and existing
legacy copies, but make the event-specific receipt reflect an actual coherent
read. The response-time controller-selection limitation is explicit and honest;
this bounded change does not promise original wire bytes for overlapping uploads.

`PlaybackSession._build_form_request` currently catches every exception and
continues (`playback.py:534`). New evidence-validation failures must escape to
the stated RequestException/result boundary; they cannot become legacy lookup,
partial form dispatch or a successful request. Existing `_execute_request` later
reopens each selected pathname (`playback.py:315`). Use verified retained bytes
for the actual multipart payload, retaining filename/MIME/form behavior, so
path replacement after validation cannot substitute the transmitted generation.
The existing requests encoder buffers those bytes already; no new upload size
policy, secret flow or transport mechanism is necessary.

## Remaining gates

Resolve P-S01 and ratify representative capture/dispatch costs before the
implementation ancestor. Actual assembler/copy/promotion and multipart tests
must include two same-name uploads, new entry absent after failure, legacy
history, duplicate IDs, corruption, malformed proofs, path substitution,
source/seed replacement and preserved event history. Run the actual profile
playback using disposable original and sandbox projects because existing lock
cleanup touches both. No implementation or package runtime approval is given.

Initial reviewed document SHA-256 values:

```text
PROFILE_TEST_ENGINE_SPEC.md e360ad25731e26081c7592b0014ed780d0d7a6c2a4f9453470e27e1a3feffb2b
profile_sbs_contract_decision.md 162503dfb644c0e195e4f30f69cfa0fe45d809e7bbb167f03f800705e6010f1d
```

## Refined design disposition

The canonical refinement adds `_sbs_seed_version: 1` to the new eligible response
event in its original append, before pointer/config/source/seed work. Marked
events require evidence even if their directory was never created. Only unmarked
historical events without an entry may use the legacy reader. This closes P-S01
without rewriting prior event history or deferring event append until capture
succeeds. The independent correctness probe
`profile_sbs_missing_entry_probe.json` confirms the original failure through
actual assembler, promotion, form selection and multipart bytes: the second
event remains recorded but transmits the first seed after an injected config
capture failure. Preserve that baseline.

The refinement also retains an upload-compatible suffix and explicitly lets
strong receipt errors escape the generic form-builder catch. No unresolved
medium/high security design finding remains in this bounded capture scope.
Representative performance ratification and actual confinement, failure,
dispatch, promotion and HTTP runtime acceptance remain open.

Reviewed refinement SHA-256 values:

```text
PROFILE_TEST_ENGINE_SPEC.md f0605a8557d8aeb8e4fe6f79d9028a9707c1823aacc3276f78b6d67ec3b54db8
profile_sbs_contract_decision.md 810d646c1c1dafc1c77d60dea05e016d34dc84c3c5246e00058735041d6c8c23
```

## Measured budget ratification

The final canonical amendment and `sbs_receipts_profile_performance_qa.md`
separate real assembler/Requests measurements, prototype composition and final
implementation acceptance. Ratify complete capture means of 100/450 ms for an
established draft and 125/550 ms for the initial draft/controller/config capture,
and verified multipart preparation means of 20/150 ms, on the two actual roughly
0.60/0.75 MB uploads and labeled 16.78 MB stress fixture respectively.

All actual confinement, opened-byte verification, generation and receipt guards
must be included in final measurements. The first composed capture was not
timed, and the prototype omitted Grizzly's 34,830-byte primary config seed even
though active-config/default writes were exercised. Final first-capture evidence
must include the complete configured primary seed; these component results do
not establish that pass. HTTP/native time, promotion/archive, aggregate seed
growth and memory observations remain separate, with no new size limit or
credential flow. No performance target authorizes a weaker receipt or fallback
to older event bytes. The checkpoint hold is closed; actual implementation and
runtime gates remain open.

Final reviewed SHA-256 values:

```text
PROFILE_TEST_ENGINE_SPEC.md 1cab08ddf127a030f12b37343b6ad3a1feb92637d014081d3c35e45e71527358
profile_sbs_contract_decision.md 3c6fe38157925c1631047f283f92c71e690432ac596321d9cc9df44820a988d0
```
