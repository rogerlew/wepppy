# Existing generic thinning classification checkpoint

Starting implementation `64665d2ac`. The operator asked to audit and
reconcile the ESDAC management tables. Native reference repair found a
second, independent failure. `ManagementSummary` accepts only classes
listed in the contemporary continental-US `disturbed.json`, while
the default Disturbed soil lookup already supports generic `thinning`
for clay loam, loam, sand loam and silt loam. The Disturbed ESDAC keys
115–117, 123 and 124 carry that existing exact class. The same class
is present in the historical Canada, Palouse and Virgin Islands tables.
The 96% cover scenario at ESDAC key 123 has its own management file.

The [mapping contract](../../../schemas/european-landuse-mapping-contract.md#existing-generic-thinning-classification)
extends only validation of the existing identifier. Keep the files,
serialized class, names, rates and selected soil rows. The profile does not
change any parameter and does not introduce an alias for unrelated or invalid
class names. Validate ordinary management summary and native file reads for
every existing generic thinning row. Verify the default texture rows chosen
through the actual Disturbed lookup and read at least one generated soil and
management scenario. Effective new map routing and fire group corrections
remain separate.

## Independent review

Both reviewers cleared this exact compatibility change. They found five
generic thinning entries in each of the four named catalogs and confirmed
that the current Disturbed paths preserve that class. Keep the existing
active lookup, run base lookup and bundled lookup precedence. Test that
unrecognized labels still fail. Use the class 123 scenario for the native
management and generated-soil control.

## Candidate results

The public summary resolver hydrated and parsed all 20 generic thinning rows
across the four catalogs. All 146 European inventory rows now constructed
management summaries. A misspelled class continued to raise a validation
error. Native management readback at key 123 preserved 0.96 interrill and
rill cover. The generated 7778 soil from an Es Fangar source profile used
the existing generic loam row with interrill erodibility 400,000 and rill
erodibility 0.00004. The default lookup still contains exactly the
four pre-existing generic texture rows.
