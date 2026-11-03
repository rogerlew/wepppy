# Current project v2: independent staging QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. **PASS for the declared public-controller
baseline invocation.** No native model was invoked by QA. Native outputs,
configured export and installed-reader acceptance remain pending; this is not
RQ, query-catalog or browser workflow parity.

Reviewed declaration:
`/wc1/runs/ro/roads-parameterization-program-20261103/current-project-v2/baseline-execution-declaration.json`,
SHA256 `12b5ddf989d98dfc928fdd6709b8a15859702d392a58dca9ca959d026ebc761c`.
Independent machine receipt: `resumption-r7-current-project-v2-staging-qa.json`,
SHA256 `12715afbf8f2b6e5a651a4fdbb3c28582dd4fd12c91bb10fe0264f15e1df8916`.

Readback verifies all **344 inputs**, exactly matching the failed v1 attempt,
plus **12 NoDb files**, **1,153 dependencies**, the matched revision 7 binaries,
effective flags and service UID 1000/GID 993. All six canonical clean targets
exist inside the fresh project: runs, output, plots, stats and the two flowpath
directories. Runs contains the declared inputs; the other five directories are
empty. No execution-start receipt exists. Original source inventory remains
identical across v1, v2 and current readback, with **3,374 entries** verified.

The byte-identical inputs retain the reviewed 66 hills, 193 OFEs, complete
2000–2015 climates, enabled UI/groundwater/PMET/snow companions, disabled frost
and unchanged withheld-material exclusion. Both watershed execution and raw
artifact retention remain enabled. Input identity permits carrying forward the
earlier parsed-material/reference findings, not a successful workflow result.

The additive preparation helper now preserves every copied clean target, rebases
NoDb paths before deserialization, and calls canonical bootstrap, cleaning,
baseflow-map and phosphorus-map initialization before full preparation. The
executor retains the hillslope interchange boundary and configured watershed
export. This directly addresses the missing plot directory without disabling
the failed stage. Failed v1 and its prelaunch reviews remain unchanged.

| Reviewed source | SHA256 |
| --- | --- |
| `current_r7_project_v2.py` | `911c81cb979b58331efa5d97a54cda59471bfb2f61656350e9b5be17b07f6006` |
| `execute_current_r7_project_v2.py` | `a30a61f2a832e6c57274c68fc857fd375132b9ffdb14befa29aa22211d8b720b` |
| `resumption-r7-current-project-v2-protocol.md` | `3e83851c0f5ae4b0324d12e2629bf86dad4431de61b35626440d68eb8a403ce5` |

No blocking staging finding remains. The public controller generates the
configured loss grid; the queued MOFE path has different orchestration and
additional cleanup/report/catalog consumers. The protocol correctly limits this
experiment to the public-controller lane. Retain the known channel PMET fallback
notice if repeated, and require complete native, export and reader evidence
before declaring this bounded workflow successful. No parameter acceptance,
default adoption or human UI approval follows from this pre-execution review.
