# Embedded Roads baseline prototype

Status: **passed isolated feasibility/parity; production wiring not implemented**.

The [prototype](parameterization_binding_prototype.py) retained all 18 current
soil/management assets as UTF-8 text and SHA256 hashes, using the proposed sorted
manifest identity. Original bytes total 167,705; the formatted baseline JSON is
177,697 bytes. No new dependency, native run or production data mutation occurred.

Exact JSON roundtrip passed. Altered text, an unallowlisted relative path, altered
baseline identity and unsupported resolver version were rejected. Changing one
asset and deleting another in a disposable repository-template copy left every
retained template byte unchanged. Ordinary file-copy and tar-member readbacks
preserved the baseline; these are not canonical WEPPcloud fork/archive tests.

The prototype directly called the existing production soil and management writers
for seven role arrangements, four textures, two surfaces and three traffic choices:
168 cases, each prepared from the repository templates and again from the retained
texts. **All 336 soil/management file pairs were byte-identical.** Existing soil and
management readers verified OFE counts, role ordering, management assignments and
soil values. This covers single-, two-, three- and reordered/multiple-OFE writer
branches, including low/no/high traffic and paved/gravel template selection.

The prototype constructs a controller without a NoDb initializer solely to invoke
its existing artifact writers. It does not implement or certify `roads.nodb`
binding, mutation locks, caching, Save/Prepare admission, per-role overrides,
canonical fork/archive/restore, UI or native execution. Those remain required
postapproval workflow tests. This evidence establishes that retained source text
can preserve current default artifact assembly without a second numerical formula.

Raw root:
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-binding-v1`.
The [receipt](parameterization-binding-results.json) binds the script, production
source, inventory, matrix reader and full raw case results. Reproduction requires
a fresh destination root; the script refuses to overwrite an existing one.

Command (exit 0):

```sh
wctl run-python docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization_binding_prototype.py /wc1/runs/ro/roads-parameterization-program-20261103/parameterization-binding-v1
```
