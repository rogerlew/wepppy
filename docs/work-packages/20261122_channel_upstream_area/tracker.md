# Channel upstream area tracker

2026-11-23 02:59 UTC. Active. Contract and compatibility plan recorded. Producer repair, fixture, consumer validation and publication in progress.

2026-11-23 03:14 UTC. Corrected and merged WBT and Peridot. Verified all 22,081 reaches through WEPP and both SWAT+ width modes. Both small native SWAT+ simulations completed. Independent review findings closed. WEPPpy validation and integration in progress.

2026-11-23 04:21 UTC. Local repair and requested validation complete. The sole failed CI test passed on the frozen commit with the required native binary. [WEPPpy PR 729](https://github.com/rogerlew/wepppy/pull/729) carries the SWAT+ repair and ADR. WBT and Peridot are merged. Production cutover and historical run regeneration remain operator actions.

2026-11-23 04:36 UTC. WEPPpy PR 729 merged. The operator requested a rebuilt common image and verified CI pin including the corrected WhiteboxTools executable. Advance the publication input to the verified WBT master revision 92dc068e2414de20d7688b00cb2c710677b9d2a3. The existing WEPPpyo3 pin b236ab0eed894e5664bdee5800c62f97f63ea81b contains the paired release. Verify both native artifacts on runner-02 before promoting the test image.

2026-11-23 04:59 UTC. [PR 730](https://github.com/rogerlew/wepppy/pull/730) merged at its approved commit. Published the paired common image and verified its native-library hash and three-reach fixture on runner-02. [Image provenance](artifacts/runner-image.md).
