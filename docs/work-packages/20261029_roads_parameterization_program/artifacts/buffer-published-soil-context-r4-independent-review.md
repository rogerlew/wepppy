# Independent review of published SOIL context

Version 3 passes independent provenance and data readback for descriptive use.
This is independent AI review, not a causal experiment or parameter acceptance.

The [executable review](review_buffer_soil_context_r4.py) checks the actual
callable's module and its loaded native library, not only a package facade.
Its [receipt](buffer-published-soil-context-r4-independent-readback.json) binds
the `.so` SHA256
`7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`,
the facade, wrapper, executed converter, fixed seeds and original source records.
All 18 raw SOIL files match their original output manifests.

Independent Arrow equality checks confirm all 18 version-2/version-3 tables
including schema metadata. Recomputed date/OFE uniqueness and full-calendar
coverage total 315,576 rows. Every non-Parquet-hash lane-summary field agrees;
the reviewer independently recomputed first/minimum/maximum/missing and first
change for roughness on all three OFEs in every lane. Different Parquet byte
hashes do not indicate different logical observations. The earlier incomplete
reader-identity attempts remain retained and are not retrospectively certified.

All nine legacy buffer histories report 100 mm roughness throughout. Six
generated histories reach 6 mm; the three selected underprediction histories
remain at 100 mm. The canonical field is millimeters, consistent with the
native water-balance writer's conversion from meter-valued roughness. These are
published, rounded histories, not evidence of unrounded bit identity.

The association is useful for prioritizing the existing SOIL branch
observations. It does not establish that roughness caused the hydrologic or
sediment differences: the entire soil profile and other conditioned parameters
differ simultaneously. Observe the actual density/consolidation condition,
roughness-decay operands and subsequent hydrologic support before proposing a
controlled ablation. No seed, input, native source, threshold or parameter was
changed, and this review ran no native model or new conversion.
