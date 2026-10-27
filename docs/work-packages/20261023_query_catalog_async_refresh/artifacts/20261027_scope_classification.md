# Completed scope classification

The read-only classification completed in 2,866.147 seconds under the existing
production batch UID 1002/GID 130. All 30,891 discovered scopes were classified;
no errors or unwritable non-READONLY scopes were recorded. This is an observation
over the probe window, not an atomic snapshot or authorization to refresh them.

| Namespace | Scopes | Writable | READONLY | Missing catalog (all scopes) |
| --- | ---: | ---: | ---: | ---: |
| wc1:runs | 5,709 | 4,609 | 1,100 | 2,622 |
| wc1:batch | 1,756 | 1,756 | 0 | 47 |
| wc1:culverts | 2,727 | 2,727 | 0 | 2,204 |
| legacy:runs | 20,699 | 9,422 | 11,277 | 20,556 |
| Total | 30,891 | 18,514 | 12,377 | 25,429 |

Missing-catalog counts include READONLY scopes; they are **not** the bootstrap
write demand. READONLY checks include the shared owner marker. Raw sample paths
remain private; sampling retained the 12 smallest SHA256 path digests per namespace
among writable scopes. Final sample membership must be compared with the earlier
exploratory snapshot before combining results.

[Aggregate](20261027_scope_classification.json),
[classifier](qcat_capacity_profile.py),
[owner concentration](20261027_owner_concentration.json).

Owner grouping uses the canonical root-layout depth on the classified locators.
All 1,756 batch scopes share eight owners (largest: 470 scopes); 2,727 culvert
scopes share 55 owners (largest: 278). Both namespaces have zero READONLY scopes
in this observation. Primary/legacy owner histograms include READONLY scopes.
Owner coordination can serialize nested scope jobs, so aggregate worker-count
scaling alone is insufficient to certify cycle or queue-wait bounds.
