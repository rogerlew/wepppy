# Shared project asset declarations

Opened 2026-11-22 UTC. Status: **scaffolded for contract review**. Target: faithful extraction of shared logical asset declarations. Implementation, unit validation, production validation and release are open.

## Outcome and scope

Define the location once at the writer and preserve what Feature Export users and query clients see. Keep the export layer catalog in Feature Export. The first vertical slice follows one fixed watershed asset and one scope-dependent WEPP loss table through the producer, export dependency plan, query catalog and named parent projection. Audit evidence includes 181 production catalogs and shows materially different child-direct and parent-qualified views. [Audit and limitations](../20261023_query_catalog_async_refresh/artifacts/declared_asset_audit/findings.md)

The proposed [canonical contract](../../schemas/shared-project-asset-declarations-contract.md) owns the shared semantics. The [ExecPlan](prompts/active/implementation_execplan.md) sequences the contract checkpoint, implementation and validation. [Tracker](tracker.md)

## Boundaries and responsibilities

Producer owners own the naming rule and selection inputs. Feature Export owns layer configuration and export behavior. Query-engine owners own public catalog keys, access, publication and reader behavior. Production operators validate actual mounted artifacts on wepp1/wepp2. Complexity budget is a shared in-process declaration interface and thin consumer adapters. Package scope excludes adding infrastructure, changing the scanner default, bulk backfill, widening catalog membership, modifying RQ admission, or cutting over production.

Security impact is **high** because source selection crosses child/parent filesystem and consumer authorization boundaries. A dedicated security review and correctness review are required at the implementation revision. The first review artifacts concern the scaffold only.

## Exit criteria

1. Commit an independently reviewed contract and decision checkpoint before implementation; reconcile conflicts with existing domain contracts.
2. Exercise both named assets through their real producer-facing naming and consumer entry points with scoped tests, including inherited, missing and denied cases.
3. Compare the exact candidate and baseline against actual normal and Omni production projects on NFS. Preserve direct and parent-qualified behavior, source identity, dependency fingerprint, schema, actual query results, export planning and joined values on the read-only original. Verify a fresh exported artifact on an isolated writable replay of the same project generation. All required matrix cells need evidence or an explicit open disposition.
4. Record separate claims for locally tested, production validated and deployed. Prior audit counts support case selection only. No unreviewed compatibility delta can pass.
