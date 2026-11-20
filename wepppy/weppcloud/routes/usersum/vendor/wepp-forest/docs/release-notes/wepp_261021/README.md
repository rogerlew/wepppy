# WEPP 261021 technical release report

Artifact revision 2 reissues the undeployed calendar-only release from source
`d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`. The report covers all shipped
changes since 261010, the watershed accounting audit and the Cedar Creek
comparison. It preserves the unresolved signed soil/routing acceptance limit.

## Build and review

From this directory, with the existing TeX installation:

```bash
mkdir -p build
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
```

`prepare_figures.py` reproduces the report figures from retained compact data
and explicitly labeled mathematical illustrations. See `change-register.csv`
for source coverage and `implementation-review.md` for separate numerical and
scientific review. Figure provenance and report-source hashes accompany the
review receipt. Published-method references are in `references.tex`.

Document revision `1` was approved for public publication by Roger Lew on
2026-10-21: “Publish the reviewed report.” The reviewed scientific content is
unchanged; final status/revision labels identify the approved edition.
`publication-manifest.json` records the approved PDF hash and public path.
The reviewed draft's hash remains in the review receipt. No legacy source
listings or attachments are included. Earlier public 261010 reports remain
unchanged. Report publication is separate from production deployment.
