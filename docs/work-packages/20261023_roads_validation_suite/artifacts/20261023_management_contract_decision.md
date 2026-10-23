# Management reference integrity checkpoint

Pilot execution of the reviewed validation suite exposed a production defect:
no-traffic single-OFE inputs fail with `iresd read as 2; must be between 1 and 1`.
The two-OFE transform also removes plant 2 while preserving road residue index 2,
silently changing the referenced plant. These are prerequisite fixes for the
authorized parameter validation, not new modeling defaults.

Amend the Roads specification, WEPP Run Assembly Contract: retain all plant
definitions and plant references; only select/remap initial/yearly OFE assignments.
Reject clamping residue indices or editing the legacy scientific templates.
No API/schema/default change. Existing projects need prepare/run to regenerate
inputs; baseline artifacts remain unchanged. Verify both traffic templates,
one/two/three/four OFEs, native execution, and full-project prepared artifacts.

Independent contract reviews and checkpoint commit precede the production edit.
