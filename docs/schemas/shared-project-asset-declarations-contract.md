# Shared project asset declarations

Status: proposed contract-first checkpoint. Runtime conformance and production acceptance are pending. The [work package](../work-packages/20261122_shared_project_asset_declarations/package.md) tracks review and evidence.

## Ownership and scope

Each migrated dataset family has one stable internal identity and one producer-owned rule for its logical location. The writer, refresh notifier, Feature Export and query catalog consume that rule. Existing public query keys, export layer/source/dependency IDs and stored project formats retain their meanings. Declarations describe exact relative keys, bounded templates or controller-selected paths. Match the existing Feature Export locator vocabulary where applicable. Resolve one supplied selector separately from enumerating a complete, producer-owned set of selectors. An export's selection of a contrast ID does not establish the valid IDs for inventory.

Feature Export owns its layer catalog, joins, column behavior, geometry, required/optional roles, display metadata and dependency fingerprints. The query engine owns discoverability, freshness, access checks, schema verification and publication. An asset reference by a consumer, including a dependency marker, grants neither query visibility nor permission to access a file. Share naming below the two consumers. Each consumer adapts a declaration into its existing contract, including its path spelling and error behavior.

The first slice covers `watershed/hillslopes.parquet` and the loss table `wepp/output/interchange/loss_pw0.hill.parquet`, including existing output-scope substitutions and named Omni projections. Baseline/Roads template expansion applies only to layers that support it today. Existing Omni scenario and contrast loss projections use their baseline paths. Production membership outside this slice continues under existing rules. Normal, scenario and contrast views resolve independently. Parent-qualified visibility is explicit. A child key in its own catalog does not add that key to the parent's listing. A layer that already resolves an explicitly qualified path can continue to use it even when the parent query catalog omits it.

## First-slice implementation

`wepppy.project_assets` names the two logical families. The Peridot postprocessor, watershed migration and WEPP loss interchange adapter use those names when publishing or checking outputs. The native Peridot and WEPPpyo3 writers have their own filename contracts. A physical rename requires coordinated native changes and readback from the resulting binaries.

Feature Export resolves declaration references when loading its layer catalog. Downstream planners and fingerprinting receive the existing locator representation. Query discovery still scans with its existing membership rules. The observer can select a declared key from an already published catalog for parity testing. Query execution remains responsible for selecting an authorized physical file.

## Identity and compatibility

- Reject duplicate declaration IDs and conflicting declarations for a canonical query key in the same project view before returning a candidate listing or publishing. Child-first precedence within one declared family remains valid. Multiple export source IDs can reference the same asset. Compare ordered entries and multiplicity as well as key lookup, so a last-write-wins dictionary cannot hide a collision.

- Scope resolution uses the actual project identity and currently selected producer output. Local scenario overrides and child-local contrast products take precedence where the owning resolver specifies them. Only existing authorized inherited sources may resolve to the parent. Handle moved projects, stale recorded roots, replaced children, missing optional outputs and readonly runs through the current consumer contracts.
- A declaration never treats a stored absolute path, user-supplied template, arbitrary NoDb getter or symlink as authority. Use validated selector values and explicit read-only controller resolution. Preserve consumer-specific containment checks before opening or hashing a selected source. Preserve the stricter query access boundary even when an export is permitted.
- For equivalent inputs, Feature Export must produce the same resolved plan, dependency entries, optional-missing state, ordering, metadata signature, fingerprint and cache identity. Existing versioned layer catalogs and legacy locators continue to load. Consumers inspecting raw locator values, including table-name expansion and geometry inference, must receive an equivalent resolved representation. A cache-key or version migration requires a separately documented change.
- Query catalog membership, key spelling, selected source, schema/field metadata and query output must match the baseline, including expected absences and denials. A missing or malformed declaration, missing source and authorization failure remain distinguishable. Never silently expand a root or fall back to the legacy path on a failed candidate comparison.
- Preserve the durable receipt, missed-notification recovery, incarnation, publication and authorization contracts across sync and async entry points. A shared descriptor gives the name; a complete publication and current eligibility establish the asset. Historic catalogs can be compared before any write or repair.

## Acceptance

The staged comparison must pass scoped tests **and** read-only comparisons on actual production projects. A synthetic fixture, an exported copy or a previous audit cannot satisfy the latter gate. Measure naming and consumer parity separately from refresh performance. The [validation plan](../work-packages/20261122_shared_project_asset_declarations/artifacts/production_validation.md) defines cohorts, evidence and mismatch disposition. Operational activation is a subsequent decision.

Related contracts govern [Feature Export](../../wepppy/nodb/mods/features_export/specification.md), [query catalog refresh](query-engine-catalog-refresh-contract.md), [HTTP access](query-engine-http-access-contract.md) and [baseline/Roads scope](output-scope-contract.md).
