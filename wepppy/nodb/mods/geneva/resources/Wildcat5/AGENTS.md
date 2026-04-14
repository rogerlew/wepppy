# Wildcat5 Notes

## Scope

This repository contains analysis work around the Excel workbook `wildcat5dec072015-64bits.xlsm`.

The workbook is treated as public domain per project context.

## Macro Extraction

The workbook is an OpenXML `.xlsm` file. Its VBA payload lives at:

- `xl/vbaProject.bin`

Artifacts produced during investigation:

- Extracted VBA source modules: `extracted_macros/wildcat5dec072015-64bits/`
- Full p-code dump: `extracted_macros/wildcat5dec072015-64bits/pcode_dump.txt`

Repeatable extraction flow:

```bash
python3 - <<'PY'
import zipfile
with zipfile.ZipFile("wildcat5dec072015-64bits.xlsm") as z:
    open("vbaProject.bin", "wb").write(z.read("xl/vbaProject.bin"))
PY

python3 -m pip install --target /tmp/oletools_extract oletools

PYTHONPATH=/tmp/oletools_extract python3 - <<'PY'
from pathlib import Path
from oletools.olevba import VBA_Parser

src = "wildcat5dec072015-64bits.xlsm"
outdir = Path("extracted_macros/wildcat5dec072015-64bits")
outdir.mkdir(parents=True, exist_ok=True)

p = VBA_Parser(src)
for _, _, name, code in p.extract_macros():
    text = code.decode("utf-8", errors="replace") if isinstance(code, bytes) else code
    (outdir / name).write_text(text, encoding="utf-8")
PY
```

To regenerate the p-code dump:

```bash
PYTHONPATH=/tmp/oletools_extract python3 -m oletools.olevba --show-pcode wildcat5dec072015-64bits.xlsm > extracted_macros/wildcat5dec072015-64bits/pcode_dump.txt 2>&1
```

## Investigation Summary

What was confirmed:

- `Workbook_Open` and `Workbook_BeforeClose` in p-code match the extracted source behavior.
- The visible external execution behavior is `ShellExecute` used to open local help PDFs.
- No downloader, PowerShell, `WScript`, `CreateObject`, `XMLHTTP`, or similar payload-style behavior was found in the reviewed p-code.

What was also confirmed:

- `olevba` reported VBA stomping, and there are real source/p-code mismatches in several modules.
- The mismatches look like stale or reshuffled compiled VBA, especially around forms and some UI/routing code, not a hidden alternate startup payload.

## Working Policy

Until there is concrete evidence that this is unwise, future work should use the extracted text modules in `extracted_macros/wildcat5dec072015-64bits/` as the authoritative working source.

That means:

- Read and modify the extracted `.bas`, `.cls`, and `.frm` files first.
- Treat `pcode_dump.txt` as a secondary verification artifact.
- Revisit the trust model only if a future task uncovers behavior that is present in p-code but not represented adequately in extracted source.
