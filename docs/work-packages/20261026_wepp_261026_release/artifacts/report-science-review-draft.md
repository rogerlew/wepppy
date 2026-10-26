# Independent draft report science review

Date: 2026-10-26. Reviewer: science_review agent. Reviewed native report source
under `docs/release-notes/wepp_261026`. Authoring files were not edited.
This is a draft review, not final publication or release signoff; incomplete
current gate counts are expected and are not findings by themselves.

## Findings to close before publication

1. **Current PDF validator still targets the old report.**
   `validate_document.py:21–22` opens the 261010 PDF/log; lines 35–40 validate
   only 261010 identities and exactly nine figures. Its final result text also
   asserts revision-2 authorization inherited from that report. A stale copied
   PDF could satisfy the wrong gate. Point validation at 261026, validate its
   current sidecars and new evidence anchors, include inherited figure assets
   in the authoring manifest, and derive publication status from this release's
   review rather than the old result string. The old coverage/register may be
   retained as explicitly historical evidence, but cannot be the sole current
   source-coverage check.

2. **Effective-support equation needs its zero-storm qualification.**
   `release-update.tex:34–38` says the existing consumer uses
   T=3600*sum(w)/max(w). That is correct for the newly eligible late path because
   storm duration is zero. General MIXRETURN uses
   max(storm,3600*sum(w)/max(w)). State that the displayed expression is the
   zero-storm specialization, or show the general expression then specialize.
   The historical methods already describe the more general rule; leaving both
   unqualified would appear inconsistent in a cumulative report.

3. **Inherited positive-duration requirement is broader than implemented.**
   `inherited-repairs.tex:237–238` says reconstructed source volume requires
   positive duration. Qualify this as the rainfall/untyped CHRQIN branch above
   its existing threshold. An explicit return-only SRC3 may legitimately have
   zero legacy storm duration—the central 261026 case. The existing subsequent
   sentence about separate return support helps, but does not eliminate the
   apparent contradiction.

4. **Historical operating instructions need local historical labels.**
   `operations.tex:48` starts an unqualified "Release Artifacts and Operational
   Use" section and tells users at lines 74–75 that a project "must select
   261010". The earlier historical preamble establishes intent, but these
   standalone instructions conflict with the current operating contract when
   readers navigate directly through the contents. Label those sections and
   instructions as historical 261010 actions and point current users to the
   261026 section. Likewise, `appendices.tex:121` should identify its "revision
   0.1 is an authored review draft" statement as historical, not current.

5. **Abstract omits the current release's central repair and inherited scope.**
   `main.tex:50–60` still frames the cumulative changes as two older problems.
   Add the late dry-day source-classification failure and the inherited calendar,
   water-allocation and channel-publication repairs. Keep the current clear
   limitation against full closure/field validation. This is a completeness
   correction, not a request to expand technical detail.

6. **Extend current change/evidence mapping.**
   `change-register.csv` contains only RN-01–10 and EX-01 from 261010 while the
   new inherited chapter uses RN-261021 identifiers and the opening chapter
   introduces 261026. Add entries or an explicit separate current mapping so
   all cumulative changes and their evidence can be traced. Keep historical
   source coverage labelled as such; do not simply relabel its 14-file count.

## Scientific scope that is already satisfactory

The opening update clearly distinguishes source classification from physical
peak/erosion correction, explicitly retains zero physical hillslope peak for
late events, describes the terminal-area volume basis, and excludes mixed,
contoured and daily-water-balance cases. It discloses midnight relocation of
late hourly bins, preserved legacy decimal quantization, and the owner's
acceptance of the approximation. Those are the important scientific limits.

Historical studies are explicitly not presented as 261026 simulations. The
inherited chapter covers Gregorian execution, groundwater area, signed hourly
allocation, flat-source overlap, channel source admission, MC live state and
reference handling, exact fixed-point copying, accepted-discharge publication,
and working-array lifetime. The update retains signed soil/routing withdrawal
and raw clipping as open and does not claim a new MC storage authority.
Neither successful execution nor source-cell integration is presented as
complete catchment conservation or observed hydrograph calibration.

The bibliography and cross-reference identifiers are internally complete in
the reviewed TeX source: no undefined citation or reference keys were found.
This was a source-level check, not a rendered-PDF layout review or independent
revalidation of historical studies. Final review still needs the frozen current
gate table, exact identities and rendered report after the above findings close.

## Correction verification checkpoint

Verified the current-report PDF/log and sidecar targets, 13-figure expectation,
zero-storm equation qualification, rainfall/untyped positive-duration wording,
historical operations headings/instructions, expanded abstract, and cumulative
change register. Those corrections address the core scientific-scope findings.
The validator result string now identifies 261026 rather than inheriting the
old report's authorization statement.

Two remaining artifact details were sent to the maintainer: appendices.tex
still contains an unqualified revision-0.1/publication-pending statement, and
the authoring manifest's figures/*.png glob omits the inherited PDF figures.
The validator also still only checks the historical 14-file source coverage
and historical numeric anchors; add explicit current mapping/anchor checks
before treating it as complete cumulative-report validation. Final gate counts
and rendered-PDF inspection remain pending by design.

## Rendered review and findings closure

Reviewed the 49-page, 13-figure PDF with SHA-256
`1e9b5a4872d878058ca4248390584545421d96f422edd006cb0f825358c130f9`, its
extracted text, current validator, and evidence receipts. All six draft findings
are closed: current artifact identities/anchors and cumulative coverage are
checked, inherited PDF figures are included recursively in the manifest,
historical appendix status is locally qualified, and the scientific wording
corrections remain present. The historical source count is now separately
named rather than presented as current coverage.

Visually inspected the new scope/effective-support/evidence pages 3–4 and the
inherited accounting/calendar page 36. Equations, figure labels, bounds and
text are legible without clipping in those samples. The calendar divisibility
symbols render correctly. The Poppler XML workaround replaces only invalid
text code points before parsing and retains all words and bounding boxes;
raw extraction and the count of two control glyphs remain recorded. This does
not remove adverse layout evidence or modify PDF scientific content. The
automated all-page bounds check reports zero out-of-page words; no embedded
files or JavaScript are reported. Visual sampling is not a claim of manual
inspection of every page or accessibility certification.

The scientific and disclosure content is acceptable for the authorized release
scope. This is conditional on inserting/reviewing the final broad-gate results,
freezing publication metadata and identities, and rerunning validation on the
final PDF. It does not treat the still-running broad gate as passed.

## Final science and report closure

Final disposition: **PASS for the documented bounded 261026 release scope**.
All prior review findings and pending gate-evidence conditions are closed.
The reviewed final report is revision 1, 49 pages and 13 figures, SHA-256
`57320794cd53e86cb0d4ce699f635042f5d52b306ca279cfaee33cf1220e3d2c`.

Verified the final non-draft document-validation receipt against the actual PDF
hash. Reviewed final gate counts, owner-authority clarification, and publication
status; visually inspected the final gate/identity page 5. Scientific methods,
equations and limitation disclosures remain as previously reviewed. The final
text correctly reports 11941 covered test nodes as 11791 passes and 150 skips,
plus one collection-module skip, rather than counting every covered node as a
pass. Earlier failed attempts and their subsequent passing results are retained.

The publication status rests on the user's release/re-versioning authorization
and completed scoped AI reviews; it is not presented as human peer review or
institutional endorsement. No scientific or report-content blocker remains for
this exact frozen PDF. The accepted midnight-support approximation, unchanged
physical hillslope peak, legacy volume quantization, and inherited signed-coupling
and clipping limitations remain explicit. This closure does not establish field
calibration, universal physical conservation, or authorize deployment.
