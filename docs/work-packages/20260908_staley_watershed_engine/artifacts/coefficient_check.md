# Independent publication check

Checked 2026-09-09 UTC against the operator-provided, gitignored 42-page
accepted manuscript `wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf`.
SHA-256: `72de34d27231acd14cc0ba8daf431e9121464132072447aef6ff658b687e660b`.
This check is independent of the specification transcription and any pfdf
implementation; it is not the final independent correctness review.

Read Table 4 visually on PDF page 36 (printed manuscript page 35), and equations
4–6 on PDF pages 15–16 (printed pages 14–15). `pdftotext -layout` omits the
equations, so rendered pages were inspected with `pdftoppm`. No PDF or page
images are added to Git.

| Model | Minutes | B | Ct | Cf | Cs | Check |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | 15 | -3.63 | 0.41 | 0.67 | 0.70 | Matches |
| M1 | 30 | -3.61 | 0.26 | 0.39 | 0.50 | Matches |
| M1 | 60 | -3.21 | 0.17 | 0.20 | 0.220 | Matches |
| M3 | 15 | -3.71 | 0.32 | 0.33 | 0.47 | Matches |
| M3 | 30 | -3.79 | 0.21 | 0.19 | 0.36 | Matches |
| M3 | 60 | -3.46 | 0.14 | 0.10 | 0.18 | Matches |

Equation 4 is B plus three rainfall-times-predictor terms, equivalent to
`B + R*(Ct*T + Cf*F + Cs*S)`. Equation 5 is
`(log(p/(1-p))-B)/(Ct*T + Cf*F + Cs*S)`. Equation 6 divides accumulation by
duration in hours. Rainfall accumulation is millimeters. The publication
discusses the inverse with positive predictor contributions and uses p=0.5;
the proposed general equality API for negative response and other targets is
an explicit mathematical extension, not a publication-derived scientific policy.

The manuscript explicitly discusses intercept-controlled, nonzero likelihood
at zero rainfall. M1's F is dNBR/1000 in the publication encoding; the existing
normalized dNBR helper already supplies that value directly.

Incidental source discrepancy to retain for future scientific guidance review:
printed manuscript page 12 states a 0.2–8 km² data range, while the current
specification states 0.02–8 km². This coefficient check does not establish which
range the final journal version supports and does not introduce an area gate.

Reproduce local inspection:

```bash
pdftotext -layout wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf /tmp/staley_engine_paper.txt
pdftoppm -f 15 -l 16 -scale-to 1400 -png wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf /tmp/staley_engine_equations
pdftoppm -f 36 -l 36 -scale-to 1400 -png wepppy/nodb/mods/postfire_debris_flow/docs/pdfs/staley_2017.pdf /tmp/staley_engine_table
```
