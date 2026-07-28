# SHR-04B Shared Contract Matrix

| Producer | Material contract | Final evidence |
| --- | --- | --- |
| `modal.js` | state, focus, keyboard, dismiss, duplicate load | direct Jest; duplicate guard repaired |
| `details_menu.js` | retained click, outside/Escape close, API, duplicate load | direct Jest; duplicate guard repaired |
| `theme.js` | stored/default/invalid theme, sync, event, storage failure, duplicate load | source/generated cross-load Jest + generated parity; duplicate guard repaired |
| `console_utils.js` | config precedence, boolean coercion, absent state, duplicate load | direct Jest; conforming |
| Console macros | controller/action/button structure | direct Jinja render; conforming |
| Table macros | page/panel structure and caller content | direct Jinja render; caller preservation repaired |
| Modal/theme templates | exact hooks, accessible names, options | direct Jinja render; conforming |

SHR-05 owns unit preference conversion. Stateful console routes and job
lifecycle remain with their registered SURF packages.

Focused evidence is 4 passing Jest tests and 108 passing rendered-template
tests. Full frontend and documentation evidence is recorded in the completed
ExecPlan.
