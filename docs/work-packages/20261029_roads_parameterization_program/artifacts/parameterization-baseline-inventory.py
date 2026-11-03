"""Read-only inventory of the production Roads baseline; no model execution."""
from pathlib import Path
import ast
import hashlib
import json
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEMPLATES = ROOT / 'wepppy/nodb/mods/roads/legacy_templates'
SOURCE = ROOT / 'wepppy/nodb/mods/roads/roads.py'
NATIVE = Path('/workdir/wepp-forest-release-20261009')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    entries = []
    for path in sorted(TEMPLATES.glob('*/*')):
        if path.suffix not in {'.sol', '.man'}:
            continue
        lines = path.read_text().splitlines()
        item = {'path': str(path.relative_to(ROOT)), 'sha256': digest(path),
                'bytes': path.stat().st_size, 'version': lines[0],
                'source_records': [{'line': i, 'text': text} for i, text in enumerate(lines, 1)]}
        if path.suffix == '.sol':
            roles = []
            for i, text in enumerate(lines):
                if not text.startswith("'"):
                    continue
                header = shlex.split(text)
                horizon = lines[i + 1].split()
                assert len(header) == 9 and len(horizon) == 6
                roles.append(dict(role=header[0], texture=header[1], layers=int(header[2]),
                    albedo=float(header[3]), initial_saturation=float(header[4]),
                    ki_kg_s_m4=float(header[5]), kr_s_m=float(header[6]),
                    critical_shear_pa=float(header[7]), avke_mm_h=float(header[8]),
                    depth_mm=float(horizon[0]), sand_pct=float(horizon[1]),
                    clay_pct=float(horizon[2]), organic_matter_pct=float(horizon[3]),
                    cec_meq_100g=float(horizon[4]), fragments_marker=horizon[5]))
            assert len(roles) == 3
            item['roles'] = roles
        entries.append(item)
    tree = ast.parse(SOURCE.read_text())
    source_rules = {}
    names = {'_default_params', '_resolve_legacy_soil_template_path', '_resolve_legacy_management_template_path',
             '_build_single_ofe_soil_file', '_build_routed_two_ofe_soil_file', '_build_routed_three_ofe_soil_file',
             '_build_routed_mofe_soil_file', '_build_single_ofe_management_file',
             '_build_routed_two_ofe_management_file', '_build_routed_mofe_management_file'}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            content = ast.get_source_segment(SOURCE.read_text(), node)
            source_rules[node.name] = {'line': node.lineno, 'sha256': hashlib.sha256(content.encode()).hexdigest()}
    native = {name: digest(NATIVE / 'src' / name) for name in ['input.for', 'tilage.for', 'scon.for', 'param.for']}
    result = {'purpose': 'Production baseline content inventory; native source readback only, no execution or calibration claim',
        'repository_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        'roads_source_sha256': digest(SOURCE), 'source_rules': source_rules,
        'native_release_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=NATIVE, text=True).strip(),
        'native_source_sha256': native, 'templates': entries,
        'counts': {'soils': sum(x['path'].endswith('.sol') for x in entries),
                   'managements': sum(x['path'].endswith('.man') for x in entries)}}
    target = Path(__file__).with_name('parameterization-baseline-inventory.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(target.relative_to(ROOT)), 'sha256': digest(target), **result['counts']}))

if __name__ == '__main__':
    main()
