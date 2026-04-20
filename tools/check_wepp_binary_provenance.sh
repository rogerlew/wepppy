#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <binary> [<binary> ...]" >&2
  exit 2
fi

EXPECTED_INTERPRETER="${EXPECTED_INTERPRETER:-/lib64/ld-linux-x86-64.so.2}"
ALLOWED_LIB_PREFIXES_REGEX="${ALLOWED_LIB_PREFIXES_REGEX:-^(/lib/|/lib64/|/usr/lib/|/usr/lib64/)}"
BANNED_PATHS_REGEX="${BANNED_PATHS_REGEX:-(/home/linuxbrew/\.linuxbrew/lib/ld\.so|/opt/homebrew/|/home/[^[:space:]]*/miniconda[^[:space:]]*/|/home/[^[:space:]]*/miniforge[^[:space:]]*/)}"

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

  interpreter="$(
    readelf -l "${bin}" 2>/dev/null \
      | sed -n 's@.*Requesting program interpreter: \(.*\)]@\1@p' \
      | head -n1
  )"
  echo "interpreter=${interpreter:-<missing>}"
  if [[ -z "${interpreter}" ]]; then
    echo "error: missing ELF interpreter entry: ${bin}" >&2
    status=1
  elif [[ "${interpreter}" != "${EXPECTED_INTERPRETER}" ]]; then
    echo "error: unexpected ELF interpreter: ${interpreter} (expected ${EXPECTED_INTERPRETER})" >&2
    status=1
  fi
  if grep -Eq "${BANNED_PATHS_REGEX}" <<<"${interpreter}"; then
    echo "error: interpreter path matches reject policy: ${interpreter}" >&2
    status=1
  fi

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

  dyn_tags="$(readelf -d "${bin}" 2>/dev/null || true)"
  rpath_lines="$(grep -E '(RPATH|RUNPATH)' <<<"${dyn_tags}" || true)"
  if [[ -n "${rpath_lines}" ]]; then
    echo "${rpath_lines}" | sed -n '1,120p'
    while IFS= read -r line; do
      path_blob="$(sed -n 's/.*\[\(.*\)\].*/\1/p' <<<"${line}")"
      IFS=':' read -r -a path_parts <<<"${path_blob}"
      for path_part in "${path_parts[@]}"; do
        [[ -z "${path_part}" ]] && continue
        if grep -Eq "${BANNED_PATHS_REGEX}" <<<"${path_part}"; then
          echo "error: banned RPATH/RUNPATH entry: ${path_part}" >&2
          status=1
        fi
        if ! grep -Eq "${ALLOWED_LIB_PREFIXES_REGEX}" <<<"${path_part}"; then
          echo "error: unexpected non-system RPATH/RUNPATH entry: ${path_part}" >&2
          status=1
        fi
      done
    done <<<"${rpath_lines}"
  fi

  ldd_out="$(ldd "${bin}" 2>&1 || true)"
  echo "${ldd_out}" | sed -n '1,120p'
  if grep -Eq "${BANNED_PATHS_REGEX}" <<<"${ldd_out}"; then
    echo "error: ldd output includes banned loader/library paths" >&2
    status=1
  fi
  while IFS= read -r resolved; do
    [[ -z "${resolved}" ]] && continue
    if ! grep -Eq "${ALLOWED_LIB_PREFIXES_REGEX}" <<<"${resolved}"; then
      echo "error: non-system resolved dependency path: ${resolved}" >&2
      status=1
    fi
  done < <(sed -n 's/.*=> \([^[:space:]]*\) (.*/\1/p' <<<"${ldd_out}")

  libgfortran_path="$(sed -n 's/.*libgfortran[^[:space:]]* => \([^[:space:]]*\) (.*/\1/p' <<<"${ldd_out}" | head -n1)"
  if [[ -z "${libgfortran_path}" ]]; then
    echo "error: libgfortran dependency not found in ldd output: ${bin}" >&2
    status=1
  elif ! grep -Eq "${ALLOWED_LIB_PREFIXES_REGEX}" <<<"${libgfortran_path}"; then
    echo "error: libgfortran is not sourced from system library paths: ${libgfortran_path}" >&2
    status=1
  fi
done

exit "${status}"
