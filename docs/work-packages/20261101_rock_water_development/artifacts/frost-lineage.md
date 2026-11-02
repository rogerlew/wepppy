# Frost activation lineage and legacy compatibility

Read-only investigation, 2026-11-01. No native executions, builds, source edits or
writes to prior evidence roots. Native source inspected at checkpoint c58ad035c.
This establishes source/history and binary-call-path facts, not executed coverage
or a complete account of historical calibration decisions.

## Policy history

| Checkpoint | Verified change | Limit |
| --- | --- | --- |
| c70bad57b, 2020-08-25 initial source import | Eligible winter hours call frostN without a KSFLAG/ksatadj gate at that call site | This import is not authenticated WEPP2010 source |
| 189e32e8a44dd1de53654426e86b4b284834f45b, 2022-07-19 | Adds per-OFE ksatadj==0 gate, together with forest conductivity adjustments and new soil-format support | Commit explicitly intends forest frost suppression and later reconsideration with regeneration routines; no calibration evidence is supplied by its message/diff |
| a3a57cb32df754586c605cdc18bf6571de39a112, 2022-08-09 | Replaces the call-site gate with KSFLAG==1; commit describes crop KSFLAG1/frost active versus other land uses KSFLAG0/frost inactive | winter.for does not include cke.inc at this revision; KSFLAG is not bound to its canonical COMMON here |
| e62bbb95087616952ada4c2fcf0bbb49e56cd16d, 2023-03-28 | Replaces winter's ctemp/cvgpar includes with cke.inc when adding 9003 support | This establishes the canonical COMMON binding; historical intervening executable behavior cannot be inferred from intended flag semantics |
| c0b07c893, 2026-04-19 | Adds frost-adjacent guard/observation work while retaining KSFLAG gate | Instrumentation is not the origin of frost suppression |

The August 2022 binding issue is a source-level finding: git grep finds KSFLAG's
include declaration only in cke.inc, absent from that winter routine's includes.
Under implicit typing it is a separate local integer, so initialization/build
behavior matters. Do not assume every binary between August 2022 and March 2023
implemented the documented global policy. No historical binary from that interval
was executed in this investigation.

A separate local upstream SVN working copy at /workdir/jimf-wepp-2023 retains a
weather-only frostN call. Read-only SQLite metadata identifies checkout revision
1375 and winter.for last-changed revision13 by jrf; infile.for last-changed
revision1334 by as. This corroborates a fork-specific divergence in these retained
sources, not a universal upstream policy. The SVN checkout is not a WEPP2010
build provenance substitute.

## Current execution semantics and confounders

Native infile.for reads header KSFLAG, normalizes invalid values to1, and later
sets the global flag to0 when the first OFE's native land-use code is not1.
winter.for permits frostN only when the weather/state gate and KSFLAG==1 both
hold. The effective flag is shared across OFEs, not an independent per-OFE frost
setting. Mixed-OFE ordering therefore needs explicit runtime observation.

Header/INFILE state is not necessarily final: SCON can set the global flag to1
when estimating first-two-layer cropland conductivity for sufficiently small
input conductivity. Its thresholds depend on soil format. Observe the flag after
SCON and at winter/INFPAR consumers before classifying a fixture as frost-disabled.

KSFLAG also controls cropland crust/tillage, canopy/cover and final effective
conductivity adjustments in INFPAR (current lines414,448,472), and rangeland
conductivity adjustment in SOIL (line598). Thus the earlier description emphasizing
rangeland conductivity was incomplete: even cropland-format Roads controls can
have coupled hydraulic changes. A KSFLAG0/1 contrast is not a frost-only contrast.

frost.txt is parsed independently. Its first value wintRed controls winter water
redistribution in WATDST, not whether frostN is called; WINTHD prints that setting.
The current GETFREEZECOND executable branches select kfactor1 for annual/bare,
kfactor2 for perennial/pasture, kfactor3 for forest. Its purpose comment reverses
indices1/3, whereas INFILE comments agree with actual branches. Follow executable
consumers, and retain this comment discrepancy as documentation debt.

## Legacy executable and configuration evidence

FSWEPP2 /workdir/fswepp2/api/wepp/bin/wepp2010 and legacy CGI
/workdir/fswepp-docker/var/www/cgi-bin/fswepp/wepp2010 are byte-identical:
SHA256 a12976166deb2b2d7c9adc0e0f23bac24d54057031a5072b4bb0a176c7c730b8.
They are statically linked, unstripped x86-64 ELF binaries; symbols include
winter_ and frostn_. Passive objdump of winter_ shows the three weather/state
comparisons followed directly by frostn_ at address0x47b6fe, without an intervening
KSFLAG/ksatadj gate. This supports a different call-site policy, but is not proof
that a particular fixture executes that call. No full authenticated2010 source
tree or compiler/build provenance was established here.

Current legacy eRMiT erm.pl explicitly selects wepp2010. Its dated2014-02-07
comment says the2010 version needs frost.txt for correct results. The January2026
commit8ecddb909cab2c62d510124130ea5a2bb9a4f6b6 added file-presence assurance and
cleanup preservation. These establish operational expectations, not the complete
original calibration design. Legacy Roads wr.pl also selects wepp2010. Its bundled
wepp2010.html explains that2000-to2010 differences include winter runoff and
forest-buffer lateral flow, varying by climate and topography.

| Tool | Retained frost.txt first line | Second line |
| --- | --- | --- |
| Legacy WEPP:Road | 0 2 2 | 1.000000 1.000000 1.000000 0.500000 |
| Legacy eRMiT | 1 2 2 | 1.000000 1.000000 1.000000 0.500000 |

FSWEPP2 frost_utils.py writes the same tool-specific controls. Its eRMiT generator
explicitly emits KSFLAG0 to hold internal conductivity constant. Roads preserves
the template header; inspected road soil templates use KSFLAG0. File presence is
therefore compatible with intended active frost and fixed conductivity in the
legacy executable; it does not establish that combination in the newer fork.

Native land-use labels are especially important: retained3inslope.man explicitly
models a forest road using Cropland input format, land-use1. Both unburned eRMiT
forest and range management examples also use native land-use1. Do not interpret
forest/range API labels as native codes or alter management to activate frost.
Current FSWEPP2 documentation says high100.man is used for the initial100-year
eRMiT stage; inspect that actual stage rather than substituting the unburned
examples as a representative complete eRMiT workflow.

## Consequence for the autonomous program

A concrete compatibility risk is established: an intentionally fixed-conductivity
legacy deck can lose frost execution when moved to the fork because KSFLAG gained
a second purpose. Source history documents intent to suppress forest frost but
does not establish a physically validated general policy, a proven numerical
necessity, or successful recalibration of eRMiT/Roads across that change.

Next controls should separately identify effective KSFLAG, per-OFE native land
use, conductivity adjustments, frost-file redistribution and actual frost calls.
Use a private frost-only intervention while retaining KSFLAG/land use/soil inputs,
then compare warm/cold and freeze/thaw behavior with paired complete histories.
Use the authenticated legacy binary as a separate executable comparator; do not
claim bitwise equivalence across different engines or infer field calibration
from agreement. Restoring frost globally is not justified by this source audit.

## Reproducible source references

Read-only commands used: git show/log/grep for the four lineage revisions; current
source inspection of INFILE, SCON, INFPAR, SOIL, WINTER, WATDST, WINTHD and
GETFREEZECOND; file/sha256sum/nm/objdump on retained wepp2010; SQLite mode=ro on
upstream SVN wc.db. No legacy source or disassembly is reproduced in this artifact.

FSWEPP2 inspected commit c0fe47499406955afc547827cdae8d02ccada432;
FSWEPP-docker inspected commit a7e65129f49528ad17631459aa3af3a01d57b0ad.
Current source hashes: winter.for
6dca46e762611ddd93e030d7fcc619af92922d614a4ddc1c44576b90ee9d86ff;
infile.for16155c92e65c4418eb8d1d753126899faed0cb0cb8552c28e4dba72c472092fb.
Legacy Roads frost.txt hash5b91b9238e53d4166c43480a5b4b047f7637834fb5e64f8c6dd7b666b4c50d57;
eRMiT frost.txt hashec75009cba9dbb53bfb0e8391f9b54ab9b608c71b746982a230cd15c00396361.
