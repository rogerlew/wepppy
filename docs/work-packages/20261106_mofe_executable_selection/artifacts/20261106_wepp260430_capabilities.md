# WEPP 260430 MOFE declaration

Operator requested wepp_260430 in the same TOPAZ/WBT MOFE release list.
This adds metadata for existing binaries; no code, default, or executable-byte
change. Native upload-reader support remains undeclared (false).

Exact bytes match wepp-forest commit dac3c950d8b16cc73774bf5ce2e7e11f80baac70
and wepp1 installed binaries:
- watershed: b11c94d8ba19deb941e4221977c4ec3437f41f612a2b816beacaca1b15563292
- hillslope: 3b2fdd2b7a9e264b84f1e7b161dfb0730d49d3cb652218139efeb3ba17d7a160

The default-branch generator from wepp-forest revision
7d4cf4b5ab24bbc825515d54f25a035062b826bb generated the paired declarations.
Original build timestamp is unknown, represented as null; metadata generation
has a separate timestamp. Source branch master describes the archival lineage,
not a claim that the historical working branch was recovered. The archived
release changelog records 20029107 plus a dirty fixed-form hotfix, captured by
dac3c950d. No rebuild or invented clean-build provenance.

Native validation used committed fixture
`tests/fixtures/mofe_coefficient_ownership/default` from source revision
7d4cf4b5ab24bbc825515d54f25a035062b826bb. Both exact installed binary roles ran
its three-OFE, 2000–2015 hillslope simulation in isolated /tmp directories.
Both exit zero, emit the success marker, and produce 17,532 finite daily WAT
rows spanning OFEs 1/2/3. Both WAT outputs hash to
e48b0215398c22601cb1d9f0dc3787b6f7e2c3824c3fe361f3c05b50da0d75b0.
PASS, loss, EBE, soil, plot and element outputs were also generated.
System loader/runtime provenance gate passed for both executables. Historical
watershed validation is retained in the archived release changelog, not rerun
or represented as a new watershed simulation here.

The sidecars preserve legacy ASCII PASS, master-pass prompt and reload flags.
Only MOFE eligibility expands. Uploaded-input projects continue to require a
separate validated reader declaration. The paired files must be installed in
web and rq-engine; capability reads are fresh, so no process restart is needed.
Rollback removes the new pair (binary files remain unchanged).

Scoped tests: 57 passed; added real 260430 save/reload and legacy PASS-family
check also passed. Independent metadata review found no correctness blocker.
Production eligibility verified on wepp1 at 2026-11-07 00:35 UTC:
web and rq-engine have both sidecars, validated against installed hashes. Actual
WEPP Exec template renders all six choices; runtime API schema includes 260430,
selection validation accepts it, and inferred PASS family remains legacy_ascii.
Saved selection remains 261029. No process, worker, or container restart.
Metadata commit dff5d4f57 pushed to origin/master. The running containers have
the metadata overlay; future images must include that commit.
