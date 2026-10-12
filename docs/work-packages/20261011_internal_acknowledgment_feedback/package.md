# Internal acknowledgment feedback

The operator requests immediate confirmation after accepting the internal
collaborator statement: remove the acceptance button and show
“You have accepted this version.” Scope is Profile acknowledgment presentation,
its membership status text, and regression evidence. PowerUser and administrative
forms, API payloads, authorization, persisted consent, and deployment are excluded.

Security impact: low; presentation only, preserving existing session/CSRF and
success/error boundaries. No dedicated security review artifact is required.
Acceptance requires successful save without navigation, hidden/removed consent
controls, accurate membership text, accessible confirmation, and retry on error.
No generated scientific artifacts or data schemas change.
