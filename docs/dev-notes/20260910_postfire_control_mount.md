# Post-fire debris-flow Mods menu repair

The run template omitted the debris-flow section and navigation containers when
the mod was disabled. `Project.toggleModSection` therefore had no insertion
target, and the dynamic bootstrap map also lacked the controller. Re-enabling
could otherwise retain a singleton bound to a removed form.

The template now retains hidden placeholders immediately after RUSLE, matching
registry order and the owner's prerequisite-based layout. Dynamic activation
remounts the controller and reveals registry-declared RUSLE/POLARIS dependencies.
Remounting detaches the previous status stream/listeners and invalidates pending
readiness responses before binding the replacement form.

This repairs the feature registry's usable-toggle policy and the shared
controller contract's idempotence across mod toggles. The layout and activation
rule is recorded in `docs/ui-docs/contracts/postfire-debris-flow-control-contract.md`,
“Scope and layout”; user guidance is in the production M1 specification.

Validation: 854 JavaScript tests across 110 suites, ESLint, the targeted run-page
ordering test, documentation lint and bundle generation passed. Authenticated
browser validation on disposable development project `lawless-challah` passed
first activation through the Mods checkbox, form/readiness rendering without
reload, placement after visible RUSLE, disable/re-enable with working form
handlers, and persistence after reload. Development web workers were reloaded.
The full Python suite remains on hold by owner instruction.
