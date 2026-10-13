# Primary onboarding documentation audit — dispositions

Date: 2026-10-13. Status: audit complete; selected operator corrections implemented (see follow-through below).
Baseline: `21fbaa7e5e7664af5b3fa3db4be51d1af7167d45`, including the operator-requested,
uncommitted User Guide model-list and FAQ Staley/OMNI/fork updates.

## Selected operator follow-through (2026-10-13)

D01, D02, D13, D14 and D18 are addressed by
[the selected-corrections package](../../work-packages/20261013_onboarding_audit_corrections/package.md),
following reviewed contract checkpoint `b4be200b4`:

- **D01:** operator chose a new default, `wepp_261010`, rather than merely documenting `wepp_260714`. Config/help/current guides updated; saved selections unchanged. Obsolete capacity wording corrected.
- **D02:** operator rejected palette-recognition rejection. Native admission now accepts readable unknown palettes and leaves colors unassigned for explicit mapping. Display Unassigned remains distinct from source NoData; four-class exports retain existing NoData semantics. Structural/native failures remain errors.
- **D13:** ORCID is indefinitely deferred by operator decision; onboarding no longer promotes it. No runtime OAuth removal is included.
- **D14:** request internal-feature access from Mariana Dobre, `mdobre@uidaho.edu`, with the feature and intended use. The PowerUser guide now gives this destination; acknowledgment alone still grants nothing.
- **D18:** the title is now **WEPPcloud FAQ**. This editorial approval does not claim independent scientific validation of every historical answer.

The remaining 13 dispositions are not implemented. The original audit evidence
and recommendations below are retained as dated findings; the decisions above
supersede the proposed D01/D02/D13/D14/D18 resolutions.

## Scope and method

Four parallel read-only reviews covered first-run onboarding, model discovery,
access/navigation, and modeling instructions. The coordinator reconciled
overlaps and checked consequential claims against source and current contracts.
This is a static documentation audit, not a production deployment inspection,
browser acceptance test, scientific validation, or external-link availability
check. Existing dirty `generated/docs_index.json` was ignored.

Primary coverage: `user-guide.md`, `getting-started.md`, `quick-start.md`,
`faq.md`, `poweruser-getting-started.md`, `feature-maturity-and-release-governance.md`,
`user-preferences.md`, `mods-overview.md`, `climate-options.md`,
`wepp-advanced-options.md`, `wepp-run-results.md`, `sbs-map-preparation.md`,
`wepp-model.md`, all 12 `models/*/ENDUSER.md` guides at discovery/entry-point
level, and the supplementary `ag_field-mod.md`. Navigation, manifest, relevant
templates, routes, registry, model modules, and canonical contracts supplied
corroborating evidence. Deeper checks concentrated on contradictions affecting
user decisions or successful execution.

Evidence shorthand below: **U/** means
`wepppy/weppcloud/routes/usersum/weppcloud/`; **T/** means
`wepppy/weppcloud/templates/`; all other paths are repository-relative.
Line numbers refer to this working-tree snapshot and will move after corrections.

## Disposition summary

The 21 agent findings consolidate to **18 dispositions**: **1 P1**, **10 P2**,
and **7 P3**. At audit completion, seventeen were accepted documentation corrections/additions
and one required a contact decision. Selected follow-through above records the
subsequent operator decisions and implementation.
None authorizes changing runtime access, model defaults, or scientific methods.

- **P1:** misleading instructions can cause a materially wrong model setup;
  correct before the next onboarding publication.
- **P2:** incorrect, incomplete, or conflicting workflow guidance; include in
  the next documentation correction pass.
- **P3:** discovery, orientation, or maintenance improvement; follow after P1/P2.
- **Accepted** means the finding is confirmed and the proposed correction is
  appropriate. It does not mean the correction has been made.

## P1: model setup

### D01 — AgFields recommends an obsolete executable

**Accepted · correct · MODEL-01.** `U/models/agricultural-fields/ENDUSER.md:100,104,169,196`
says to retain/select `wepp_dcc52a6` and warns against newer builds.
`wepppy/nodb/configs/ag-fields.cfg:35` selects `wepp_260714`;
`T/controls/ag_fields_pure.htm:349–353` identifies that current default as
capacity-32 and corpus-tested. A reader can replace the intended default by
following the guide. Update all occurrences and the historical warning;
preserve the distinction between parent-watershed and AgFields selections.
Reference current validation provenance rather than implying every newer
executable is suitable. Do not change the configured executable in this fix.
The adjacent capacity claim at `U/models/agricultural-fields/ENDUSER.md:195`
also needs correction: it says 20 plant scenarios, while current production
synthesis permits 32 distinct referenced yearly scenarios
(`wepppy/nodb/mods/ag_fields/README.md:150–155`,
`wepppy/wepp/management/utils/multi_ofe.py:16`). Keep that management-scenario
limit distinct from the independent Concept 1 planner's 20-OFE limit.

## P2: workflow correctness and completeness

### D02 — SBS recovery instructions can require an impossible next step

**Accepted · correct · SCI-01.** `U/sbs-map-preparation.md:46,54–58,116` advises
uploading unsupported palettes and correcting assignments in the interface.
`wepppy/nodb/mods/baer/sbs_map.py:505–508` rejects invalid existing color tables;
`wepppy/microservices/rq_engine/upload_disturbed_routes.py:115–117` returns 400
before the map is available for editing. Distinguish accepted maps needing
class reassignment from rejected palettes. For rejection, describe GIS-side
remapping to supported colors or exporting valid numeric classes without the
palette, followed by re-upload and verification. Preserve in-app correction
guidance for successful uploads; do not weaken upload admission.

### D03 — Executable reference omits capability and full-rerun requirements

**Accepted · add · SCI-02.** `U/wepp-advanced-options.md:509–535` describes binary
selection and watershed-only execution but only says MOFE needs newer binaries.
`T/controls/wepp_pure_advanced_options/wepp_bin.htm:18–24,52` requires declared
MOFE support and a hillslope-plus-watershed rerun after changing releases.
Bring those requirements into the reference so users do not mix intermediate
outputs from different releases. Link the existing accurate Config Builder
summary in `U/user-guide.md:104–111`; do not create a second selection policy.

### D04 — Internal-feature descriptions confuse maturity, roles, and membership

**Accepted · correct · START-05 + MODEL-03.** `U/user-guide.md:80` says internal
features are limited to Dev; `U/mods-overview.md:10` says OpenET is shown to
Admin users; `U/models/batch-runs/ENDUSER.md:31,144` uses Admin/operator and
preview language. Registry entries in
`wepppy/weppcloud/feature_registry/feature_registry.yaml:20–31,252–263` define
OpenET and Batch as internal and group-only. The authoritative distinction is
in `docs/schemas/feature-access-governance-contract.md:116–118,130` and
`wepppy/weppcloud/utils/feature_access.py:66–85`.
Separate maturity from entitlement, distinguish discovery from permission to
operate, and explain membership plus applicable acknowledgment. Admin/Root/Dev
must not be described as blanket group-only exemptions.

### D05 — Getting Started still describes administrator-only elevation

**Accepted · correct · START-03 + ACCESS-01.**
`U/getting-started.md:28–29,316–329` promises account API tokens, describes
Profile as read-only, and sends readers toward administrative role grants.
`wepppy/weppcloud/routes/user.py:83,604` restricts token minting;
`T/user/_poweruser_access.html:23–35` provides self-service PowerUser activation.
Qualify token eligibility and document Profile → PowerUser access, immediate
activation, and the separate Root role-management workflow. Link
`U/poweruser-getting-started.md`; preserve the existing grant/statement contract.

### D06 — Model discovery omits current modules and their entry requirements

**Accepted · add · MODEL-04.** `U/mods-overview.md:1–84` omits Geneva, Staley
post-fire debris flow, and AgFields. The Roads and AgFields guides begin their
workflows without explaining how an eligible user obtains the control
(`U/models/roads/ENDUSER.md:15–30`,
`U/models/agricultural-fields/ENDUSER.md:15–24`). Registry evidence:
`wepppy/weppcloud/feature_registry/feature_registry.yaml:130–154,220–232,269–281`.
Add short access/backend/start instructions: Roads is PowerUser-gated with WBT
(respecting the existing elevated-role behavior); Geneva requires WBT; Staley
requires WBT and Disturbed; AgFields follows its internal role-or-group policy.
Link the common access explanation instead of maintaining independent policy
prose in every guide. Do not add entries to protected navigation sections as
part of this correction without the required explicit authorization.

### D07 — AgFields onboarding omits the fifth stage

**Accepted · add · MODEL-02.** `U/models/agricultural-fields/ENDUSER.md:17–24,169–170`
stops at four stages. `T/controls/ag_fields_pure.htm:365–396` offers
**Integrate the Watershed**, three routing schemes, and running all schemes.
Explain the optional integration step, separate output trees, entry prerequisites,
and interpretation differences. Explicitly preserve the direct-injection
limitation: no buffer routing. Implementation availability is not evidence that
every routing choice is scientifically suitable for every site.

### D08 — Fork/archive descriptions omit when copied state is captured

**Accepted · correct/add · START-02.** `U/getting-started.md:204–217,227–232`
describes a point-in-time archive without explaining queue delay.
`T/controls/archive_console_control.htm:50` and
`T/controls/fork_console_control.htm:43` already tell users state is captured
when the worker starts and to avoid edits while queued/running. Carry that
guidance into onboarding, including restore replacing current project files.

### D09 — Archive onboarding does not explain retention and independent backup

**Accepted · add · START-01.** `U/getting-started.md:223–232` recommends archives
to preserve milestones and says they live inside the project, but omits TTL
and download guidance. `U/run-ttl-deletion.md:8–29` explains scheduled deletion;
`wepppy/rq/project_rq_delete.py:98` removes the project tree. Explain that a
server-side archive is not independent protection against project deletion;
download important snapshots and link Project TTL Deletion. Do not promise a
fixed retention period or broaden eligibility for disabling TTL.

### D10 — Quick Start gives conflicting outlet instructions

**Accepted · correct · START-06.** `U/quick-start.md:140–154` says **Use Cursor**,
then recommends longitude/latitude; its summary at `:292` requires coordinates
without supplying them. The actual manual mode is **Specify lon/lat**
(`T/controls/set_outlet_pure.htm:23–37,67–87`). Choose one reproducible path for
the supplied Rattlesnake example and keep the alternative optional. If adding
copyable coordinates, verify their outlet placement against the example before
publication; do not invent coordinates from the screenshot.

### D11 — More-menu walkthrough is behind the delivered navigation

**Accepted · correct/add · ACCESS-02 + START-07; overlaps START-03.**
`U/getting-started.md:288–335` omits GL Dashboard and calls the panel's token
section **Actions**. The ordinary authorized-user dashboard link is at
`T/header/_run_header_fixed.htm:190–209`; the section is now
**Analyze and troubleshoot** (`T/controls/poweruser_panel.htm:228–229`). Add
GL Dashboard with prepared-data/access qualifications and correct the label.
Use D05's shared panel eligibility/activation guidance. Conditional Config
Summary and TTL controls can be linked without making the inventory exhaustive.

## P3: orientation and maintenance

### D12 — Config Builder instructions omit menu visibility conditions

**Accepted with narrowed scope · clarify navigation · START-04.**
`U/getting-started.md:102–107` says authenticated users can open Config Builder
from Interfaces. The link is under More and visible to PowerUser/Dev/Admin/Root
(`T/interfaces.htm:32–49`). However, the route itself is only login-gated
(`wepppy/weppcloud/routes/weppcloud_site.py:1022–1026`), as independently noted
by ACCESS. Document where the link appears and provide activation guidance.
Do not falsely state that ordinary authenticated users are forbidden from the
route, or change route authorization under a documentation task. This is a
navigation distinction, not a confirmed unauthorized-access defect.

### D13 — OAuth provider guidance is incomplete

**Accepted · qualify by deployment · ACCESS-04.** `U/getting-started.md:35–42`
lists only Google/GitHub; `U/user-guide.md:130` also names ORCID.
`T/security/login_user.html:27,49` and `wepppy/weppcloud/configuration.py:227–259`
implement conditional ORCID support. Tell readers to use the providers shown
on Sign In and include ORCID when enabled. Static support does not establish
that a provider is enabled on every deployment.

### D14 — Internal-access guidance lacks an actionable request destination

**Needs contact decision · add after confirmation · ACCESS-03.**
`U/poweruser-getting-started.md:47–52` correctly explains separate permission
but gives no request destination. `U/feature-maturity-and-release-governance.md:579–615`
permits collaborators subject to maintainer approval. Confirm a maintained
contact/request route, then add it with the feature and intended-use information
to supply. Do not invent a form, promise approval, or equate acknowledgment with
membership. This gap does not require changing authorization.

### D15 — WEPP model guide's Soil Options inventory omits anisotropy

**Accepted · add/link · MODEL-05.** `U/models/wepp/ENDUSER.md:41` lacks the
upper/lower controls. `T/controls/wepp_pure_advanced_options/soil_anisotropy.htm:2–16`
and `docs/schemas/soil-anisotropy-contract.md:7,13` supply eligibility and behavior.
Add a concise pointer to the already-current `U/wepp-advanced-options.md`:
MOFE + hourly water balance + deep seepage; upper 1–100, lower 1–10;
horizon-bottom classification at 50 cm; blanks preserve source values; values
above 10 can cause numerical instability. Avoid duplicating the full contract.

### D16 — Supplementary AgFields page mixes historical proposals with delivery

**Accepted · label/reorganize · MODEL-06.** `U/ag_field-mod.md:26,507,642–643` reads
as unfinished design while `:683–692` records completed implementation; current
controls expose the three schemes at `T/controls/ag_fields_pure.htm:377–380`.
Add an upfront current-status summary and end-user guide link, and explicitly
label historical proposal sections. Preserve unresolved scientific qualification
instead of marking all historical acceptance concerns complete.

### D17 — Results guide lacks the OMNI-versus-fork choice

**Accepted · cross-reference · SCI-03.** `U/wepp-run-results.md:175–186` recommends
an undisturbed fork without mentioning OMNI. The comparison use case is covered
by `wepppy/nodb/mods/omni/ENDUSER.md:21–36` and the new FAQ at `U/faq.md:58–65`.
Keep the working fork instructions; add the shared-climate/shared-WEPP-options
versus independent-settings distinction and link the FAQ.

### D18 — FAQ's blanket Legacy Draft title obscures its status

**Accepted · editorial follow-up · SCI-04.** `U/faq.md:1` still says
**WEPPcloud FAQ (Legacy Draft)** despite current maintained instructions.
After the substantive corrections are reviewed, remove the blanket qualifier
or mark individual historical answers requiring review. Renaming is not a
scientific validation of all remaining claims.

## Retained content, rejected concerns, and unresolved verification

- **Retain the operator's current model-list and FAQ edits.** AgFields has a UI;
  Cannon and Staley are distinct workflows. Staley M1/M3 likelihood, 50% rainfall
  intensity, preview status, and no volume/runout claims agree with
  `wepppy/nodb/mods/postfire_debris_flow/ENDUSER.md:3–28,66–75`. PATH-CE's mulch
  optimization scope matches its user guide. The OMNI/fork distinction is sound.
- **Reject the suspected quick-start image prefix defect.** Development and
  production Caddy explicitly serve `/usersum/static/*` as well as the prefixed
  alias (`docker/caddy/Caddyfile:159–167`, `docker/caddy/Caddyfile.wepp1:149–157`).
  Source paths alone do not establish a broken deployed image.
- **Do not extend DAYMET's documented availability based on the current date.**
  `wepppy/nodb/locales/climate_catalog.py:14,211` still pins 2024. No correction
  was established in Climate Options during this review.
- **Do not remove the Run Results GL Dashboard link as stale.** It remains in
  `T/controls/wepp_reports.htm:129–134` alongside the More-menu destination.
- **No missing PowerUser-guide registration.** It is in the manifest and
  Advanced and Operations navigation. Its activation/recovery, existing-role,
  Admin/Root, private-run, and acknowledgment guidance matches the contract.
- **User Preferences matched implementation.** Units, boundary handling,
  automatic save/retry, and initiating-user semantics were consistent.
- **No confirmed consequential entry-point defect in Ash, RHEM, Revegetation,
  RUSLE, DSS, or SWAT+ in this bounded pass.** This does not certify their
  scientific behavior or every API detail. Existing Roads output separation and
  WBT guidance should be retained.
- **Geneva's technical-specification link is valid.** A shorter end-user guide
  would improve orientation, but the existing link is not broken; optional
  follow-up, not an additional confirmed defect.
- **Scientific and deployment claims remain outside this evidence.** Historical
  scientific generalizations and cross-tool uniqueness claims in the FAQ/WEPP
  Model were not independently revalidated. Live provider enablement, screenshots,
  production parity, personnel details, and external URL availability were not
  certified. Do not label them correct merely because this audit found no local
  contradiction.

## Validation and recommended correction sequence

- `wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud`: **46 files,
  zero errors/warnings**.
- `wctl exec weppcloud python /workdir/wepppy/tools/usersum_docs_tool.py validate
  --require-vendor-files`: **76 documents, 76 navigation leaves, two vendors**,
  contracts valid; read-only operation.
- Relative Markdown-target existence scan: **45 files**, zero missing local
  targets after excluding commented markup. This was not an anchor, HTTP-status,
  image-rendering, or semantic correctness test.
- Final access/model reviewer spot checks confirmed the consolidated
  dispositions; the AgFields capacity correction and historical-section line
  reference were incorporated. The disposition report itself passes doc lint.

1. Correct D01–D03 first: executable setup and actionable upload recovery.
2. Reconcile D04–D07 and D11–D12 together to keep discovery, eligibility, and
   actual entry instructions consistent across the overview and linked guides.
3. Complete D08–D10 for reliable first-run operation and project preservation.
4. Address D13 and D15–D18; resolve D14's contact route before publishing it.
5. Lint changed docs, verify links and affected UI instructions, and rebuild the
   usersum index when publishing catalog/search changes through the existing
   delivery workflow. No index rebuild, service restart, or production change
   was performed for this audit.

Small maintenance improvement: when a shipped UI/default/access change alters
onboarding, review both its canonical guide and the model/Getting Started
summaries in the same change. The current drift is semantic; adding another
Markdown linter would not have caught these contradictions.
