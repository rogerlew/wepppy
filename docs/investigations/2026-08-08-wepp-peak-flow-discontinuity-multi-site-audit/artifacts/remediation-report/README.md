# Remediation report figures and provenance

The October 6 report update adds remediation analysis without modifying the
three closed experimental work packages. No model was rerun and no executable,
production run, parameter default or external stakeholder message was changed.

## Figure sources

Revised PDF Figures 1–3 use the original PNGs directly from
`docs/work-packages/20261006_surface_return_mutation/artifacts/figure-{1,2,3}.png`.
The original August plots remain in the historical results, with automatically
updated figure references. They are not relabeled as candidate results.

The four original-versus-candidate comparison figures are consumed directly from
`docs/work-packages/20261006_warming_rrinit_legacy/artifacts/comparison/`.
Their methods, selection rules, JSON summaries and hashes remain there.

The totalwatsed figures and sidecars in this directory are byte-preserving
copies of the completed October 6 follow-up. The producer is
`plot_totalwatsed.py`, with `totalwatsed-comparison.json` and `selection.json`.
Raw inputs remain in the corresponding `warming-rrinit-totalwatsed-20261006`
research directory on forest, under its `rr10`, `rr17`, and `rr60` lanes.
These curves represent daily pre-channel yield, not routed instantaneous flow.
`figure-manifest.json` records sizes and SHA-256 hashes for every PNG consumed
by the report, plus the copied plotting script and numerical sidecars.

## Rebuild and validation

From the investigation directory, run `pdflatex -halt-on-error
-interaction=nonstopmode topanga-small-mutation-census-report.tex` twice.
Relative figure paths require the retained work-package directories in the
same repository tree. A temporary mirror with that layout may be used for
compilation; never build into or edit a closed work package.

Check the log for undefined references, missing graphics and overfull boxes.
Extract the PDF text and verify the key numbers, figure order and qualification
of historical results. Render and visually inspect all pages. The PDF is the
user-facing artifact: successful compilation alone is not acceptance.

This is a report-only update; application tests and model reruns are not
applicable. The documented hydrograph-volume release gate remains unresolved.

## Completed checks

The final PDF has 38 pages and 13 figures. Two-pass pdfLaTeX compilation on
forest succeeded without undefined references, missing graphics or overfull
boxes. Page renders were visually reviewed; the revised captions and final
bibliography were checked again after the last layout adjustment.

`verify_report.py` (Python with pypdf) checks all figure dependencies, local
README links, key numerical statements in extracted PDF text, and sequential
figure captions. It generates `figure-manifest.json` and `verification.json`,
including the final PDF hash. Both edited Markdown files pass `markdown-doc
lint` with zero errors and warnings; `git diff --check` passes. Markdown lint
used a temporary repository-layout mirror with the real link targets copied
into place; local path existence is independently checked by the verifier.

The writing review kept the original census explicitly historical, separated
within-build roughness effects from between-build changes, and retained adverse
validation findings in the abstract, main assessment and current conclusion.
