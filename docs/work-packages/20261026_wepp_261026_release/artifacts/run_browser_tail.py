import os,json
from pathlib import Path
import pytest
root=Path(__file__).parent
cache=Path('/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers')
assert (cache/'chromium_headless_shell-1194/chrome-linux/headless_shell').is_file()
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(cache)
os.environ['MYPY_CACHE_DIR']='/tmp/mypy_cache'
modules=json.loads((root/'browser-tail-modules.json').read_text())
raise SystemExit(pytest.main([*modules,'--maxfail=1','--report-log='+str(root/'tail-1-r3.jsonl')]))
