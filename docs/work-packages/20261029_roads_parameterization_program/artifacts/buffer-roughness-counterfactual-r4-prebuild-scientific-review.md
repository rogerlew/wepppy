# Independent scientific prebuild review: roughness persistence U1

Disposition: approve the frozen isolated candidate for compilation only. This is
independent AI scientific review, not institutional peer review. Runtime,
interpretation, parameterization and release acceptance remain open.

The four-file patch preserves the original model statements. The only added
assignment to model state restores buffer RRC to its captured native initialized
value. Capture follows the cropland initialization; restoration follows all
native SOIL roughness writers and precedes INFPAR and the subsequent critical
shear adjustment. The other three files add observations at assigned consumer
values. Natural roughness-dependent conductivity, friction, interrill delivery,
shear, thermal and subsequent hydrologic responses remain active.

The helper checks three-OFE continuous cropland context, buffer no-tillage and
unchanged RRINIT. The configured IRSYST must be zero. NOIRR at this SOIL point is
carried prior irrigation state, not proof of current-day irrigation absence.
Initialization uses a literal phase/date and does not read the daily calendar.
Native initialization assigns the recorded density operands before the helper;
CBR is observed only after its assignment in the decay branch. Active/inactive
crust observations exclude unassigned active-branch locals. Friction and class
delivery observations follow their native computations. Existing O3 observations
retain the resulting detachment and theta values.

Two scientific observation issues were corrected before freezing: RKECUM is
cumulative rainfall kinetic energy in J/m², with CKE in m²/J in its exponent;
it is distinct from precipitation-depth RFCUM. Also, U1's native pre-restore
roughness belongs to the treated history. If a native writer is skipped, it may
retain yesterday's held value. Same-call pre/post equality therefore cannot
prove historical nonintervention; compare separate complete off/on histories.

Exact BD/POR and their fixed driver trajectories remain declared controls.
Native RH/SMRM and assigned CBR are observed endogenous responses, never extra
clamped states. The configured 100 mm roughness can eliminate native cropland
interrill delivery; a sediment change must not be attributed only to depression
storage. Forest management labels do not establish physical calibration.

Independent readback verified all 977 base files, the calendar sibling, all 978
staged files, four candidate sources, exact reconstructed patch, source-preserving
line sequence, toolchain/library hashes and the successful make dry-run receipt.
Python preparation/build scripts were syntax-checked without execution. The
companion JSON binds the exact map, patch, manifest, staging and build driver.
No compilation or native simulation was performed by this reviewer.

A separate runner review and post-build provenance gate must precede the four-run
first-pair preflight. Require the off-lane ordinary-output parity, predicted
native-bit null controls, full-period state/isolation checks and unchanged strict
physical/particle audits before interpreting any result. Passing this gate does
not accept outcomes or authorize parameter promotion.
