# Comrak migration security review

The reviewer confirmed that the renderer owns safe options and that
callers can select only the three approved extension settings.
The application exposes only a URL destination callback. Comrak
checks URLs after replacement. Preview and Browse use direct rendering.
The reviewer separately checked both rendering modes with each
supported option enabled, including raw HTML, links and images.

Repeated rendering exposed a resource retention bug in the Python AST
binding. Its parent and child references form cycles that Python GC
does not track. With the original AST round trip, 1,000 SBS manual
renders raised RSS from about 31 MiB after the first 200 to 94 MiB
after the final 200. The binding reconstructs native formatting nodes
from child references alone. The adapter now clears all parent
references before calling application code. Regression tests cover
inspection, image descendants and exception cleanup. In a final
warm-process check, measured RSS stayed at 38,328 KiB from batch 200
through batch 1,000 while repeating both AST render and inspection.
The reviewer independently confirmed stable RSS and matching HTML.

The candidate image contains `comrak-ext` 0.2.8 with native Comrak
0.59.0 in its wheel SBOM. Neither cmarkgfm nor the plain `comrak`
distribution is installed. The dependency evaluation records the
Syntect theme dependency advisories and why the exposed paths do not
reach the affected XML parser. No medium review finding remains.
