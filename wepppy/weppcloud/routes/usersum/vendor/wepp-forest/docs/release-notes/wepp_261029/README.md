# WEPP 261029 water accounting and hourly return flow

Revision 1 describes retained local inputs, proportional upstream return timing,
updated-stock ET, rooted-layer accumulation, fixed-width peak overflow printing
and retained portability changes. Owner accepted the draft; independent AI
scientific, implementation and disclosure reviews found no substantive blockers.
The report states modeling limits and adverse event differences explicitly.

Build figures with `python figures.py`. From this directory, compile twice with
`pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex`.
Inspect the final PDF, text and logs. Approved public artifacts are the PDF and
publication-manifest-r1.json only. Source/figure hashes are retained in
evidence/source-freeze-r1.json; publication-review.md records owner and review
provenance. No source patches or raw runs are public attachments.

Native implementation and evidence: ../../work-packages/20261030-hourly-return-flow-timing/.
The WEPPpy release package records vendoring, actual selection/reader and HTTP
publication gates. Existing defaults, historical releases and deployment remain
unchanged.

## Revision 2

The owner authorized replacement of the undeployed 261029 artifact under its
existing release name. [Revision-2 authoring and handoff](REVISION-2.md) covers
the additional melt, event-state, storage, deposition, sorting and channel
repairs, including shared hillslope/channel Yalin-factor cancellation.
Final matched scientific review accepts source `ba9f2ad91b51`, with 24-year
channel signs, semantic and particle checks passing. Cedar sediment increases
187.456% versus the original release; Roads magnitude targets remain unmet.

Build `main-r2.tex` separately and preserve revision-1 source and provenance.
[Revision-2 publication review](publication-review-r2.md) records the independent
reviews and publication status; `publication-manifest-r2.json` identifies the
PDF and exact matched binary pair. Final publication is separate from vendoring
and deployment; no project default changes are authorized by this report.

## Revision 4

The authorized undeployed same-name re-release adds bounded deposition search,
complete erosion-interval support, stiff integration, consistent capacity/load
boundaries, wet-coordinate ownership and the rounded PARAM denominator sign
repair. Source `b01a739957bef5aacf35b4a89bc13eddc9d94804` matches all 489 retained
build inputs; promotion preserves the exact scientifically accepted U12 pair.

The [seven-page supplement](main-r4.tex) and two original figures were reviewed
independently; [final manifest verification](evidence/final-manifest-verification-r4.json)
binds the approved PDF and publication manifest. The frozen `REVISION-4.md`
authoring note predates final pagination and says six pages; final PDF and
manifest correctly record seven. Preserve the frozen evidence bytes.

Cedar water/soil outputs are identical to revision 3; outlet sediment changes
+1.20 kg over 24 years. Roads magnitude remains unmet. Two strict fraction flags
and terminal-capacity precision retain explicit bounded explanations. No
parameter defaults, new Windows release or production deployment is included.
WEPPpy's active Roads program records exact-byte vendoring, application selection,
reader checks and HTTP delivery; earlier reports remain immutable.


## Revision 6

[Revision6](REVISION-6.md) corrects FC/HK layer/OFE ownership in native source
`b581352b6`, following reviewed contract ancestors. Existing PMET capacity and
mapped selection are verified for this source. The three-page supplement
`main-r6.tex` quantifies heterogeneous output consequences and retains9005/RAP
compatibility and scientific limits. Prior reports and evidence remain immutable.
The matched Linux pair is locally vendored; no deployment/default switch is
included. Public attachments are only the reviewed PDF and source-free manifest.

The [full configured application supplement](evidence/application-full-context-r6.json)
corrects the initial copied-project evidence attribution: partial preparation
omitted enabled baseflow/UI companions. Complete preparation and all 72 native
consumption logs now pass; installed readers accept 504 fresh outputs. Revision 5
and revision 6 are byte-identical on these same 363 inputs. Adding the companions
changes 433 outputs relative to partial preparation; those contexts are retained
separately. This supplements the frozen report without changing its bytes or
generalizing the project-specific parity result.

## Revision 7

[Revision 7](REVISION-7.md) adds reference-preserving specialized 9005 soil and
RAP/revegetation consumers. The separate `main-r7.tex` supplement records the
scientific ownership decision, numerical consequences, exact identities and
release gates. Revision 6 and earlier reports remain immutable. Public
attachments are only the reviewed PDF and source-free provenance manifest.
