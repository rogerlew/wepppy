# GL Dashboard navigation (PUUX-01A)

Status: operator-authorized 2026-10-13; independent contract reviews passed at checkpoint 5528224f6;
implemented and locally validated. Production deployment not claimed.

## Access and placement

GL Dashboard is a normal project-viewing destination, not a PowerUser benefit.
Every viewer authorized to view a run shall find **GL Dashboard** in its **More**
menu, on both the run page and reports using the shared report header. Place the
link immediately after Browse, outside PowerUser/Admin/Root conditions. Use the
existing run-aware URL helper and current viewed run/config, preserving child-run
resolution and the established open-links-in-new-tabs preference. Remove the
redundant link from the PowerUser Panel.

The existing dashboard route must retain normal project authorization. This
navigation change does not make private projects public, grant roles, enable
internal actions or imply that every run already has every dashboard dataset.
Authorized public/anonymous viewing keeps its existing behavior; authentication
is not a new navigation condition. Normal absent-output handling is unchanged.

Rationale: regular users need a discoverable analysis destination without
acquiring unrelated elevated tools. Keep the remaining PowerUser Panel and its
permissions unchanged in this bounded change. Broader onboarding work remains
pending under PUUX-01.

## Validation

Render both menus for ordinary, PowerUser and authorized public viewers; verify
one dashboard link per menu using the current run/config. Verify the link is not
inside a role condition and the panel no longer duplicates it. Confirm the
existing dashboard route still authorizes the requested project. No scientific
calculation, output-scope, dataset, model execution or feature-role change is
included. Reuse the shared controller presentation conventions and existing
project-access contract; this contract owns navigation only.
