# Tracker

## Progress

2026-10-29 UTC: all five active Caddy definitions parse with MPTCP disabled.
Operator enabled Serve; both Tailscale HTTPS login pages return 200 with valid TLS.
Domain/auth/port cutover completed on both hosts. Forest authenticated project,
report, download, profile and WebSocket probes pass; operator confirms login.
Forest1 authenticated local-password acceptance awaits operator verification.

## Decisions

Local username/password login only, no OAuth, on both homelab hosts. Preserve
accounts and passwords. Use existing Tailscale Serve and Caddy; keep public
presets unchanged by default. Bind homelab service ports to loopback with a
separate forest Redis tailnet exception for companion workers.

## Remaining

Source correctness, QA and security reviews pass; artifacts retained. Forest1
login verification and saved companion Redis credential mismatch remain open. Both
host sysctls are now zero and Serve MPTCP listeners were replaced; unrelated old
listeners remain (forest loopback11434, forest1 tailnet18080). User owns pfSense
cleanup. Kernel fixes remain required.

2026-10-29 20:29 UTC: operator-authorized Caddy-only rollout completed on wepp1.
Only Caddy changed; other 24 containers retain IDs/start times. MPTCP zero and
HTTPS health/login/job API pass. See runtime evidence for command and scope.
