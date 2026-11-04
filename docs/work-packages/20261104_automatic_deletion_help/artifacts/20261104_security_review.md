# Security review

Independent reviewer: `ttl_security`. Impact: low. Final verdict: pass; no high
or medium findings. Authorized selection, SQL freshness, null unknown state,
escaped template attributes, text-node rendering and server-generated help links
remain intact. Authentication, CSRF and retention/persistence rules are unchanged.
The help excludes manual deletion and deletion already started from its promise.

Low observation: server rendering assumes context-normalized expiration. The
existing context calls ensure_ttl_state before rendering; controller rendering
also checks date validity. Malformed response regression confirms unavailable
status. Real route auth/CSRF and persistence tests remain in the prior repair.
