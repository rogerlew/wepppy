import argparse, os
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--output', required=True); a=p.parse_args()
if os.environ.get('FAKE_CONTROLLER_FAILURE') == '1': raise SystemExit(72)
Path(a.output).write_text('candidate controllers', encoding='utf-8')
Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8').write('controller-builder\n')
