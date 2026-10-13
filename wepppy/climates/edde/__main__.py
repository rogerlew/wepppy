"""Run with python -m wepppy.climates.edde --help."""
import argparse
from pathlib import Path

from .client import EddeClient, Point, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['inventory', 'query'])
    parser.add_argument('--model', required=True)
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--year', type=int)
    parser.add_argument('--start')
    parser.add_argument('--end')
    parser.add_argument('--point', action='append', help='name,longitude,latitude; repeat for batch')
    parser.add_argument('--variables', nargs='+', default=['prday', 'tsmax', 'tsmin'])
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-download-bytes', type=int, default=4_000_000_000)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    client = EddeClient(args.cache, max_download_bytes=args.max_download_bytes)
    if args.operation == 'inventory':
        if args.year is None:
            parser.error('inventory requires --year')
        write_json(output / 'inventory.json', client.inventory(args.model, args.scenario, args.year))
        return
    if not args.point or not args.start or not args.end:
        parser.error('query requires --point, --start and --end')
    points = []
    for value in args.point:
        name, lon, lat = value.split(',')
        points.append(Point(name, float(lon), float(lat)))
    # Mark a new attempt before acquisition: an earlier completed result cannot
    # be mistaken for this attempt if acquisition fails.
    write_json(output / 'manifest.json', {'status':'incomplete', 'request':vars(args)})
    table, manifest = client.query(points, args.model, args.scenario, args.start, args.end, args.variables)
    table.to_csv(output / 'daily.csv', index=False)
    manifest['daily_sha256'] = sha256(output / 'daily.csv')
    write_json(output / 'manifest.json', manifest)
    print(f'{len(table)} point-days; {manifest["transferred_bytes"]} downloaded bytes')


if __name__ == '__main__':
    main()
