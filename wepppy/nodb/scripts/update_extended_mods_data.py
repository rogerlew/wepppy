#!/usr/bin/env python3
"""
Utility for relinking heavy location assets to EXTENDED_MODS_DATA in NoDb configs.

Typical usage (dry run):
    python wepppy/nodb/scripts/update_extended_mods_data.py

Apply modifications in place:
    python wepppy/nodb/scripts/update_extended_mods_data.py --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = ROOT / 'configs'

MAPPINGS: Dict[str, str] = {
    'portland': 'wepppy-locations-portland',
    'seattle': 'wepppy-locations-seattle',
    'lt': 'wepppy-locations-laketahoe',
}


def build_replacements(selected_locations: Iterable[str]) -> Dict[str, str]:
    replacements: Dict[str, str] = {}
    for key in selected_locations:
        repo_folder = MAPPINGS[key]
        replacements[f'MODS_DIR/locations/{key}'] = f'EXTENDED_MODS_DATA/{repo_folder}'
    return replacements


def rewrite_content(content: str, replacements: Dict[str, str]) -> str:
    updated = content
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    return updated


def relink_configs(config_dir: Path, replacements: Dict[str, str], apply: bool) -> List[Path]:
    changed_files: List[Path] = []
    for cfg in sorted(config_dir.rglob('*.cfg')):
        original = cfg.read_text(encoding='utf-8')
        updated = rewrite_content(original, replacements)
        if updated == original:
            continue
        changed_files.append(cfg)
        if apply:
            cfg.write_text(updated, encoding='utf-8')
    return changed_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--configs-root',
        type=Path,
        default=CONFIGS_DIR,
        help='Path to the configs directory (default: %(default)s)',
    )
    parser.add_argument(
        '--locations',
        nargs='+',
        choices=sorted(MAPPINGS),
        default=sorted(MAPPINGS),
        help='Subset of locations to relink (default: %(default)s)',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Persist changes to disk (otherwise run as a dry-run)',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    replacements = build_replacements(args.locations)
    changed = relink_configs(args.configs_root, replacements, args.apply)

    if not changed:
        print('No files required updates.')
        return

    if args.apply:
        print(f'Updated {len(changed)} file(s):')
    else:
        print(f'{len(changed)} file(s) would be modified:')

    for path in changed:
        print(f' - {path}')


if __name__ == '__main__':
    main()
