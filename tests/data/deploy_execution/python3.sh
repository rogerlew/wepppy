#!/bin/bash
set -euo pipefail
if [[ "${1:-}" == *"tools/check_deployment_governance.py" ]]; then
    printf 'governance|check\n' >> "${FAKE_COMMAND_LOG}"
    if [ "${FAKE_GOVERNANCE_FAILURE:-0}" = 1 ]; then exit 89; fi
    exit 0
fi
if [[ "${1:-}" == *"tools/security/retained_candidate.py" ]]; then
    /bin/cat >/dev/null
    printf 'retained|%s\n' "${2:-}" >> "${FAKE_COMMAND_LOG}"
    if [ "${2:-}" = "record-activation" ]; then
        previous=""
        for argument in "$@"; do
            if [ "${previous}" = --known-good-rows ]; then
                cp "${argument}" "${FAKE_KNOWN_ROWS_RETAINED}"
            fi
            previous="${argument}"
        done
    fi
    if [ "${2:-}" = "prepare-images" ]; then
        if [ "${FAKE_IMPORT_IMAGES_FAILURE}" = 1 ]; then exit 2; fi
        "${REAL_PYTHON}" -c 'import json,os; print(json.dumps({"images": {name:"sha256:"+"0"*63+"1" for name in os.environ["FAKE_SERVICES"].splitlines()}}))'
        exit 0
    fi
    if [ "${2:-}" = "create" ]; then
        printf '{"approval":"%s","receipt":"%s","receipt_sha256":"%064d"}\n' \
            "${FAKE_APPROVAL}" "${FAKE_RECEIPT}" 1
        exit 0
    fi
    if [ "${2:-}" = "gate" ]; then
        count=0
        [ ! -f "${FAKE_GATE_COUNT}" ] || count="$(cat "${FAKE_GATE_COUNT}")"
        count=$((count + 1))
        printf '%s\n' "${count}" > "${FAKE_GATE_COUNT}"
        if [ "${FAKE_GATE_FAILURE_CALL:-0}" = "${count}" ]; then
            exit 2
        fi
    fi
    printf '{"activation_config":"%s","approval":"%s","image_override":"%s","receipt":"%s"}\n' \
        "${FAKE_ACTIVATION_CONFIG}" "${FAKE_APPROVAL}" \
        "${FAKE_IMAGE_OVERRIDE}" "${FAKE_RECEIPT}"
    exit 0
fi
exec "${REAL_PYTHON}" "$@"
