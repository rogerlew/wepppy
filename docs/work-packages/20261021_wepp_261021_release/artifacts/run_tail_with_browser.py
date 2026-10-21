"""Run remaining validation using the already installed browser cache."""
import json
import os
from pathlib import Path
import pytest

root = Path('/workdir/wepppy')
browsers = root / 'wepppy/weppcloud/static-src/.playwright-browsers'
assert (browsers / 'chromium_headless_shell-1194/chrome-linux/headless_shell').is_file()
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers)
os.environ['MYPY_CACHE_DIR'] = '/tmp/mypy_cache'
modules = json.loads((Path(__file__).parent / 'tail-suite-modules.json').read_text())
raise SystemExit(pytest.main([*modules, '--maxfail=1']))
