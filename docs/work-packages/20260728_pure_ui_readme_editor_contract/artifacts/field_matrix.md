# SURF-09 README Editor Contract Matrix

| Boundary | Risk-bearing contract | Required evidence |
| --- | --- | --- |
| Viewer host | authorized run, safe rendered Markdown, permission-aware Edit action | route + direct render |
| Editor host | owner/admin, non-readonly, current Markdown and UUID | route + direct render |
| Bootstrap | JSON-safe run/config/UUID/Ron values and fixed run URLs | direct render |
| Preview | string Markdown, CSRF-compatible POST, non-executable HTML | inline Jest + route |
| Save | string Markdown and editor UUID, owner/admin and non-readonly | inline Jest + route |
| Lock | one active UUID, stale tab denied before write, invalidation UI | inline Jest + Redis route test |
| Persistence | fixed `active_root/README.md`, atomic/confined write, reload value | filesystem route test |
| Ron refresh | response shape updates title/command state consistently | inline Jest + route |
| Raw/poll | authorized fixed README read plus lock state for caller UUID | inline Jest + route |
| Security | auth, CSRF, ownership, readonly, confined atomic path, bounded request/render, interpolation-only Jinja | dedicated review passed |

Arbitrary file paths, Markdown feature expansion, and shared transport ownership
are excluded.
