# SURF-15 Root User Modification Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Page authority | Root-only GET | real Root/Admin route test |
| User inventory | all users; escaped identity/login metadata; empty state | real producer + actual renders |
| Role controls | PowerUser/Admin/Dev/Root names and checked state | actual selected-state render |
| Self Root | acting Root cannot remove own Root role | disabled render + persisted server rejection |
| Client request | exact endpoint, POST JSON, same-origin credentials, CSRF | actual inline Jest |
| Client failure | rollback and visible escaped status | response/JSON/network Jest |
| Request validation | JSON object, target, allowlisted role, boolean state | parametrized route tests |
| Mutation | datastore grant/revoke, commit, redundant-change rejection | real SQLite/datastore routes |
| Reload | persisted role state re-renders | post-mutation actual route render |
| Security | no Admin access, privilege escalation, CSRF bypass, or unsafe output | dedicated review PASS |
