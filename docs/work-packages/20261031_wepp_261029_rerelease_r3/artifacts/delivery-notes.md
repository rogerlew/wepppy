# Delivery evidence notes

- Native source: `6112b68bce0e21a77f510bde5c24af067a47a647`; fixture commit
  `986ffe6e4d23ea7116ccb9309474ddbc799107e7`. Native delivery commit
  `eb601ce8d` records binaries, sidecars, report and retained investigation; pushed
  to the verified default branch. The binary source identity remains `6112b68bc`.
- All 711 staged native files matched working bytes before commit. Original
  forensic logs/patches retain whitespace; scoped source/contracts/report checks
  pass. The generated D1 SVG likewise retains its original renderer whitespace.
- WEPPpy sidecars preserve features, capacities and existing runtime contracts.
  `capability-readback.json` and `vendor-revision3.json` bind installed identities.
- Local Caddy HTTP checks bind the exact approved PDF/manifest and rendered
  existing navigation. This is local publication, not production deployment.
- Application coverage uses committed base plus final binaries and provisional
  capability sidecars in a detached worktree. Final enriched sidecars/publication
  are checked separately in the actual workspace. No unrelated dirty application
  changes are claimed as validated or included in this release.
- The first application setup was interrupted after registry rejection of a
  partial staging pair. The initial shard-3 mocked-deployment timeout and first
  replay's overlong AF_UNIX temporary path are retained. The unchanged complete
  shard replay passes; no test or timeout assertion was weakened.

- The final shard also exposed an incorrect explicit browser path (`/ms-playwright`).
  The existing canonical `.playwright-browsers` directory contains the required
  Chromium. Restore that environment path and replay the failed module and full
  remaining tail unchanged; subtract seven duplicate passing tests.
