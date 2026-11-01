# Finite final-hour flux observation declaration

Three full 16-year model invocations only: zero-ks1 and normal-ks1 year3/day19–20;
high-ks1 year7/day343–344. All 17 runtime inputs are copied byte-for-byte from the
accepted reset targeted histories, including original observer markers. No new
forcing, effective parameter, geometry, period or target-date choice is allowed.

Build a private observer from the complete pinned preceding build, adding only
83 fixed-form logging lines to watbal_hourly.for, evap.for and evappm.for from
prepared-v3. The first build failed before model execution because a caller
log referenced routine-local ET; v3 reserves that caller slot as zero and keeps
ET observation inside the routines. Prepared-v1 is superseded before any build: unneeded DDRain outside
its valid call branch was removed in v2. All native arithmetic/assignments remain
unchanged. Internal ET REQUEST/RETURN tags must be enclosed by the actual final-
hour caller tags, matching day/OFE/method; orphan calls fail reader acceptance.

The runner binds all source/include/object/calendar/build members, preparer,
prepared sources/patches, public reader/controls/runner/contract/declaration,
accepted inputs and comparators, compiler/make/gcc/assembler/linker/subprograms,
ldd and five runtime libraries. Independent exact scientific and implementation
approvals bind freeze.json before building or running. PATH=/usr/bin:/bin,
FC=/usr/bin/gfortran, existing make flags retained, build timeout300seconds;
three serial model processes each900seconds. New linked runtime must match the
pinned library set. Every invocation and failed attempt is retained.

Acceptance: successful native completion, all17,532dailykeys, exact seven ordinary
outputs, exact entire frost trace, exact old BPO records after filtering only the
declared new tag set, complete ordered144hourly and6dailygroups, strict finite
values and independent actual readback. Physical comparison residuals are
reported separately from observer structural/parity acceptance. See ownership-
contract.md for equations and predeclared arithmetic/zeroing allowances.

No native model invocation may continue after failed execution, parity or support
validation. Corrected reader evidence must be separately versioned; no executed
freeze, source, input or accepted raw root may be rewritten. No physical repair,
annual-budget claim or parameter promotion is authorized by observational parity.
