# Revision 2 authoring and handoff

Final matched U10 science and independent PDF/manifest reviews accept the repair.
Approved artifacts are copied to the local WEPPpy static path and HTTP-verified;
no production deployment is claimed. Exact receipts and identities are recorded in
[publication-review-r2.md](publication-review-r2.md). Preserve every revision-1
source, PDF, manifest, freeze and review as history.

The owner explicitly authorized replacing the undeployed original `wepp_261029`
pair under the same tag. This exception does not authorize silent replacement
of ordinary deployed releases. Sidecars and the public manifest distinguish
both generations by exact source and SHA256 values.

Final source is `ba9f2ad91b5165d5cd2954bd64b5df608798541e`; watershed SHA256
`819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`;
hillslope `21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed`.
Actual-byte gates pass: 1059 native tests, 840 Roads physical/accounting cases,
99 Disturbed tests, 18 watchlist cases and two smokes. Final Cedar accepts
7,573,824 PASS and 16,690,464 WAT records with zero rejections; observed/unobserved
standard outputs agree exactly and the full 24-year intermediate class audit
has zero negative/nonfinite records. Sixteen detail dates cover 5936 channel
events and 29680 source-class records. Local closure is not a global budget.

Final outlet sediment is 517815.77 kg versus 180137.20 kg in the original
release (+187.456%); U10 differs from diagnostic U9a by one printed daily
value, -0.01 kg. All eleven reviewed daily water/source/peak fields equal U9a.
The broad increase is attributed to recovered incoming transport at prior
artificial channel sinks, with less bed erosion on the five largest increases.
No measured-sediment calibration is claimed. Roads meaningful comparisons
719/766 and small-reference comparisons 30/74 both fail their separate frozen
95% magnitude gate; 749/840 is only a combined descriptive count.

The compact `evidence/r2/U10-final-science.json` binds the independent receipts.
`change-register-r2.csv` and `evidence/source-coverage-r2.json` cover all 21
changed source/binary paths through final source ba9f2ad91. Earlier U9a builds
are diagnostic: experimental U9a inherited Homebrew binutils 2.46.1 while the
final pair uses system binutils 2.42. Source equality never transfers executable
identity; all final acceptance uses the actual dated pair.

## Reproducible authoring commands

Run from `docs/release-notes/wepp_261029/` in the canonical native checkout:

```bash
/workdir/wepppy/.venv/bin/python figures-r2.py
mkdir -p build/r2
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build/r2 main-r2.tex
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build/r2 main-r2.tex
pdftotext -layout build/r2/main-r2.pdf build/r2/main-r2.txt
pdfinfo build/r2/main-r2.pdf > build/r2/pdf-info.txt
pdfdetach -list build/r2/main-r2.pdf > build/r2/attachments.txt
pdfinfo -url build/r2/main-r2.pdf > build/r2/links.txt
pdftoppm -scale-to 1600 -png build/r2/main-r2.pdf build/r2/page
```

Use the existing WEPPpy environment for Matplotlib; the system Python here does
not have it installed. No new plotting dependency is introduced.
Figure data are copied numerical fields from the retained native receipts.
`evidence/r2/defect-controls.json` records original receipt hashes. Its plot
generator creates five new vector/PDF and PNG figure pairs. The report also
reuses the original local-input figure, whose bytes remain unchanged. No model
rerun, fitted values, raw source or private filesystem paths enter the figures.

## Final issue procedure

1. Compile twice and inspect complete text, logs, rendered pages, metadata,
   links and attachments. Freeze every included TeX/figure and final PDF in
   `evidence/source-freeze-r2.json`; the bibliography is inline in `main-r2.tex`.
2. Obtain independent scientific, implementation and disclosure decisions on
   the final PDF/manifest. `/root/publication_review` authored revision 2 and
   cannot independently approve it; its prior disclosure approval covers r1
   only. Owner acceptance of r1 is not represented as reading these sections.
3. After approval copy only `build/r2/main-r2.pdf` without rebuilding to
   WEPPpy `wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r2.pdf`
   and the public `publication-manifest-r2.json`. Preserve r1 public files.
4. Verify copied and actual HTTP-downloaded SHA256, HTTP 200 and
   `application/pdf` at
   `/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r2.pdf`.
   Root owns public copying, navigation, Usersum changelog sync and integration.
   No deployment or new route is part of this authoring handoff.

Native `change-log.md` records the accepted revision-2 repair and marks the
original row superseded before deployment, preserving its full prior notes.
The root orchestrator owns active plans, tracker and binary promotion. Commit
the authoring source, figures, internal provenance and reviewed manifest with
those release changes. No final PDF copy belongs in native `docs/`.
