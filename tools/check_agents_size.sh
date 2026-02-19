#!/usr/bin/env bash
set -euo pipefail

target="${1:-AGENTS.md}"
max_lines="${AGENTS_MAX_LINES:-160}"
recommended_min_lines="${AGENTS_MIN_LINES:-100}"

if [[ ! -f "${target}" ]]; then
  echo "AGENTS size check failed: file not found: ${target}" >&2
  exit 2
fi

line_count="$(wc -l < "${target}")"

if (( line_count > max_lines )); then
  echo "AGENTS size check failed: ${target} has ${line_count} lines (max ${max_lines})." >&2
  exit 1
fi

echo "AGENTS size check passed: ${target} has ${line_count} lines (max ${max_lines})."

if (( line_count < recommended_min_lines )); then
  echo "AGENTS size check warning: ${target} is below the recommended lower bound (${recommended_min_lines})." >&2
fi
