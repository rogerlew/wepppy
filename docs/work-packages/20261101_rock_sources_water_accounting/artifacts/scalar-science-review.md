# Scientific prereview: unchanged-source scalar probes

Disposition: approved for the declared bounded invocation, subject to the separate
implementation review. This is approval to observe unchanged source fragments,
not approval for a native capacity correction or a full-model run.

The nine initialization fixtures test SCON's actual dry-floor and capacity
arithmetic. Six overflow fixtures distinguish no-input frozen behavior, positive
input branch selection and the daily/hourly surface threshold. Holding ice and
dry reference fixed makes the declared sum(ST)+SURDRA invariant sufficient for
these isolated transfers. FIN is correctly treated as a branch selector rather
than an injected flux in the extracted block.

The two drainage fixtures test a genuine domain prerequisite: the diagnostic
operands have strict dry/field/effective-capacity ordering but UL=DRFC. With the
bottom layer and ST=DRFC, the surrounding native eligibility condition is true;
the extracted ratio encounters0/0. Expected trapping must remain reported as an
inadmissible diagnostic state, alongside the successful native control. It is
not evidence that this state occurred in a retained model history. The declared
2e-8m closure bound is acceptable for these small single-precision fixtures;
retain actual signed residuals and independent float32 comparisons.

Limitations are explicit and acceptable: TILAGE predecessor assignment, complete
HK initialization, percolation/ET/tile/lateral coupling and FRWATC/frost mapping
are not executed by this declaration. Passing it will not close those gates or
prove general frozen-water conservation. Do not enlarge its conclusions to the
prior586 initialized layers or complete annual histories. A later frozen-mapping
probe needs its own state/support and threshold declaration.

Bindings verified before this approval:

- scalar-declaration.md SHA256 `f9c128e0ffd5781abd3a3db8411f5c8d75f0351962baddeb23a9d87d628f3ca2`.
- scalar-source-declaration.json SHA256 `ce6af1ca0b956867575dc1ea4233b780b71c977f464106ee362c030907002406`.
- All three native file hashes match the declaration; exact listed slices were read.
