# Independent correctness review: optional Discord imports

Reviewer: independent `reviewer` agent, 2026-10-08; read-only static review. Scope: four RQ import guards, their new subprocess regression, and optional-configuration documentation. No production operations or notifications.

No blocking findings. Guards match existing core WEPP handling and catch only missing/unreadable optional files. Logging imports exist, configured senders remain intact, and caller sites handle `None`. The regression exercises the project import chain without leaking replacement modules into other tests. No queue, authentication, locking, or delivery-time behavior changes.

Residual coverage: no explicit absent-package or unrelated-import-exception cases were added; those handlers are unchanged. Production worker imports and a successful fork remain necessary before declaring the incident resolved. After review, the test was marked slow and adjusted to reuse the suite's Redis isolation inside subprocesses; production code was unchanged.
