# Rust CLI Medium advisory dispositions

Date: 2026-11-14

Source scan: `20261114_rust_cli_remediation_grype.json`, Grype 0.121.3,
database schema 6.1.10 built 2026-11-14 06:19:25 UTC. The scan contains 72
Medium package matches collapsing to the 42 unique IDs below. These are
candidate dispositions, not a waiver of a reachable vulnerability. The next
exact-image scan must confirm removal of the five pip findings and must be
re-reviewed if an affected API/tool becomes part of the request path.

The service accepts ZIP files only through its own bounded Python ZIP reader,
starts only the fixed Rust parser executable, runs non-root with no capabilities
and a read-only root filesystem, has no login/session/systemd service, and does
not accept SQL, package indexes, terminal descriptions, locale configuration,
DNS configuration, or command arguments from requests. Platform Security owns
the watch list. Any change to those assumptions, the base digest, installed
packages, parser linkage, locale, command, or mounts triggers fresh disposition.

| Advisory | Affected artifact(s) | Request-path assessment | Disposition |
|---|---|---|---|
| CVE-2025-12781 | CPython 3.12.16 | Vulnerable `base64` decoding APIs are not imported or invoked. | Retain with non-reachability; rescan on base refresh. |
| CVE-2025-15366 | CPython 3.12.16 | `imaplib` is not imported; no mail command input exists. | Retain with non-reachability. |
| CVE-2025-15367 | CPython 3.12.16 | `poplib` is not imported; no mail command input exists. | Retain with non-reachability. |
| CVE-2025-6141 | ncurses/tinfo packages | The service has no terminal and never parses attacker-supplied termcap data. | Retain with non-reachability. |
| CVE-2026-114690 | GCC/libstdc++ packages | The affected parallel-search API is not used by the Rust parser or Python request path. | Retain with linkage/API non-reachability. |
| CVE-2026-114691 | GCC/libstdc++ packages | The affected `vector<bool>` construction API is not used by the Rust parser or Python request path. | Retain with linkage/API non-reachability. |
| CVE-2026-115819 | glibc | The service does not call the affected wide `scanf` family. | Retain with API non-reachability. |
| CVE-2026-116566 | CPython 3.12.16 | Uvicorn binds a fixed configured host; requests cannot supply `getaddrinfo` host/port values. | Retain with fixed-input non-reachability. |
| CVE-2026-119371 | SQLite | No request opens or supplies a SQLite database or SQL expression. | Retain with data-path non-reachability. |
| CVE-2026-119372 | SQLite FTS3/FTS4 | No request opens SQLite; the service does not use FTS extensions. | Retain with extension non-reachability. |
| CVE-2026-119375 | SQLite WAL | No request opens SQLite or supplies a WAL file. | Retain with data-path non-reachability. |
| CVE-2026-119376 | SQLite | No request opens SQLite or supplies SQL expressions. | Retain with data-path non-reachability. |
| CVE-2026-119378 | SQLite R-Tree | No request opens SQLite; the service does not use the R-Tree extension. | Retain with extension non-reachability. |
| CVE-2026-119591 | SQLite | No request opens SQLite or supplies SQL views/expressions. | Retain with data-path non-reachability. |
| CVE-2026-15059 | systemd/udev libraries | No systemd-oomd service or its IPC API exists in the container. | Retain with service non-reachability. |
| CVE-2026-15534 | Perl | Perl and its regular-expression engine are not invoked by the runtime command or request path. | Retain with executable non-reachability. |
| CVE-2026-16742 | systemd/udev libraries | No systemd-homed service, local login, or homed user exists. | Retain with service non-reachability. |
| CVE-2026-18374 | glibc | The service does not construct attacker-controlled `fopen` mode strings. | Retain with API/input non-reachability. |
| CVE-2026-18477 | GNU tar | The runtime never invokes tar; uploads are admitted only as bounded ZIP archives. | Retain with executable non-reachability. |
| CVE-2026-18508 | GNU tar | The runtime never invokes tar or its `--one-top-level` extraction mode. | Retain with executable non-reachability. |
| CVE-2026-19542 | glibc | The service does not call `tdelete`. | Retain with API non-reachability. |
| CVE-2026-3184 | util-linux/login packages | The container has no login flow and never invokes `login -h`. | Retain with executable/non-root non-reachability. |
| CVE-2026-3446 | CPython 3.12.16 | Vulnerable `base64` decoding APIs are not imported or invoked. | Retain with non-reachability; rescan on base refresh. |
| CVE-2026-42250 | bzip2 library | The affected `bzip2recover` utility is never invoked; ZIP admission does not delegate to it. | Retain with executable non-reachability. |
| CVE-2026-50812 | SQLite session extension | No request opens SQLite; the session extension is not used. | Retain with extension non-reachability. |
| CVE-2026-50813 | SQLite session extension | No request opens SQLite; the session extension is not used. | Retain with extension non-reachability. |
| CVE-2026-54371 | attr package | The service never invokes `getfattr`/`setfattr`, is non-root, and has a read-only root. | Retain with executable/privilege non-reachability. |
| CVE-2026-54411 | PAM packages | There is no PAM authentication, `pam_userdb`, or local login path. | Retain with service non-reachability. |
| CVE-2026-5704 | GNU tar | The runtime never invokes tar; upload extraction uses the bounded ZIP-only implementation. | Retain with executable non-reachability. |
| CVE-2026-6019 | CPython 3.12.16 | `http.cookies.Morsel.js_output` is not used; the service emits no cookie-generated script. | Retain with API non-reachability. |
| CVE-2026-6238 | glibc resolver | The deprecated affected resolver-printing APIs are not called. | Retain with API non-reachability. |
| CVE-2026-6791 | glibc word expansion | The service does not perform shell/word expansion or accept usernames for tilde expansion. | Retain with API/input non-reachability. |
| CVE-2026-77117 | glibc iconv | The parser uses Rust `encoding_rs`; it neither selects SHIFT_JISX0213 nor invokes glibc iconv on request data. | Retain with encoding-path non-reachability. |
| CVE-2026-80489 | glibc iconv | The parser uses Rust `encoding_rs`; it neither selects EUC_JISX0213 nor invokes glibc iconv on request data. | Retain with encoding-path non-reachability. |
| CVE-2026-8674 | glibc resolver | `/etc/resolv.conf` and process environment are image/operator inputs, not upload inputs; the fixed service command does not alter resolver search lists. | Retain with trusted-configuration assumption. |
| CVE-2026-86805 | glibc dynamic loader | Requests cannot modify libraries or loader paths under the read-only, non-root runtime. | Retain with filesystem/privilege non-reachability. |
| CVE-2026-89092 | glibc nscd | nscd is not running in the container; requests cannot select DNS queries. | Retain with service non-reachability. |
| GHSA-4xh5-x5gv-qwph | system pip 25.0.1 | pip is not required at runtime. | Remove pip files from the final runtime image; exact-image scan must prove absence. |
| GHSA-58qw-9mgm-455v | system pip 25.0.1 | pip is not required at runtime. | Remove pip files from the final runtime image; exact-image scan must prove absence. |
| GHSA-jp4c-xjxw-mgf9 | system pip 25.0.1 | pip is not required at runtime. | Remove pip files from the final runtime image; exact-image scan must prove absence. |
| GHSA-qwm4-qh6w-59xr | system pip 25.0.1 | pip is not required at runtime. | Remove pip files from the final runtime image; exact-image scan must prove absence. |
| GHSA-wf93-45jw-7689 | system pip 25.0.1 | pip is not required at runtime. | Remove pip files from the final runtime image; exact-image scan must prove absence. |

## Acceptance rule

This disposition passes only if the rebuilt image still has zero Critical
findings, introduces no new unique High/Medium finding, removes all five pip
findings, and independent security review agrees that each retained advisory is
outside the fixed service request path. A fixed base/package release supersedes
the disposition: refresh the immutable digest/snapshot and requalify rather than
permanently accepting the old package.
