# Dedicated query catalog queue tracker

| Milestone | Disposition |
| --- | --- |
| Contract | Authorized 2026-11-23 UTC. Baseline 160fb12b1. |
| Implementation and scoped tests | Runtime commit c0259be33. All 137 scoped routing, admission and pilot cases passed across split runs. Deployment execution passed 75 cases, with 91 topology/tooling and six focused recovery cases passing in stable runs. |
| Independent correctness and security review | Independent security review passed for c0259be33 with zero open medium or high findings. Independent correctness review passed with a real RQ fork worker and disposable Redis. See the [review](artifacts/correctness_review.md) and [security assessment](artifacts/security_review.md). |
| Integration, build and rollout | PR [#732](https://github.com/rogerlew/wepppy/pull/732) merged at dacf4185d. The wepp1 build and both peer stages retained identical image b6e0462f8a74. Fresh scan comparison and isolated NFS publication passed. The operator accepted the image-specific risk. All three hosts passed serving activation. |
| Production validation | Preflight passed cross-host lock and publication checks on Rocket and identified the same legacy project scopes on all hosts. See [production acceptance](artifacts/production_acceptance.md). The staged worker published and acknowledged a private managed receipt in 0.637 seconds. Both NFS clients verified its bytes and values. Live acceptance passed. Both clients verified a fresh publication in 0.732 seconds. A checked archive overlapped catalog inventory for 0.610 seconds. Long-term fleet freshness remains an operational observation. |
