# Runs table sorting and layout repair

Status: contract checkpoint preparation. Scope: stable wrapping columns, repeatable
expiration sort, confirmed-disabled rows last for that sort, and one help link
at the top of the Table card. No changes to authorization, TTL mutation, scheduler,
model outputs or projection activation. Security impact: high (existing catalog
route/presentation surface); dedicated independent security review required.

Execution: [ExecPlan](prompts/active/implementation_execplan.md).
