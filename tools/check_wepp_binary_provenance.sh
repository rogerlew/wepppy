#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <binary> [<binary> ...]" >&2
  exit 2
fi

status=0

for bin in "$@"; do
  if [[ ! -x "${bin}" ]]; then
    echo "error: not executable: ${bin}" >&2
    status=1
    continue
  fi

  echo
  echo "== ${bin} =="
  sha256sum "${bin}"

  comment="$(readelf -p .comment "${bin}" 2>/dev/null || true)"
  echo "${comment}" | sed -n '1,120p'

  if ! grep -q 'GCC:' <<<"${comment}"; then
    echo "error: missing GCC marker in .comment: ${bin}" >&2
    status=1
  fi

  if grep -Eqi 'Intel\(R\)' <<<"${comment}"; then
    echo "error: Intel compiler marker found in .comment: ${bin}" >&2
    status=1
  fi

  if strings "${bin}" | grep -Eq 'for_diags_intel\.c|Intel\(R\) oneAPI|__intel_'; then
    echo "error: Intel runtime fingerprint found in binary strings: ${bin}" >&2
    status=1
  fi

  ldd "${bin}" | sed -n '1,120p'
done

exit "${status}"
