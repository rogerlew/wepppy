"""Inventory syntactic writer and notification evidence; run from the audited checkout.

Usage: python index_writers.py > writer_sites.tsv
"""
import ast
from collections import Counter
import csv
from pathlib import Path
import subprocess
import sys
import tokenize


NOTICE = {
    'request_catalog_refresh', 'record_catalog_refresh', 'update_catalog_entry',
    '_update_catalog_entry', '_refresh_catalog', 'activate_query_engine',
}
FORMATS = {
    'to_parquet', 'write_parquet', 'write_table', 'ParquetWriter', 'to_csv',
    'to_file', 'to_raster', 'CreateCopy', 'to_json', 'write_geotiff',
    'write_geojson', 'write_json', 'atomic_json', 'write_tif',
}
PUBLISH = {
    'copyfile', 'copytree', 'copy2', 'symlink', 'symlink_to', 'replace',
    'rename', 'atomic_write', 'write_text', 'write_bytes',
}


def classify(node, name):
    if name in NOTICE:
        return 'catalog API'
    if name == 'call_wepppyo3_interchange':
        return 'native dispatch'
    if name in FORMATS or ast.unparse(node.func) in {'json.dump', 'shutil.copy', 'shutil.copyfileobj'}:
        return 'serializer candidate'
    if name in PUBLISH and (name != 'replace' or not node.args or len(node.args) < 2
                            or ast.unparse(node.func) == 'os.replace'):
        return 'file publication candidate'
    if name == 'open':
        modes = [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
        modes.extend(kw.value.value for kw in node.keywords
                     if kw.arg == 'mode' and isinstance(kw.value, ast.Constant))
        if any(isinstance(mode, str) and mode in {
            'w', 'wb', 'wt', 'a', 'ab', 'at', 'x', 'xb', 'w+', 'wb+', 'r+'
        } for mode in modes):
            return 'write-mode open candidate'
    if name in {'execute', 'sql'} and node.args and 'COPY ' in ast.unparse(node.args[0]).upper():
        return 'SQL COPY candidate'
    return None


class Visitor(ast.NodeVisitor):
    def __init__(self, path, writer):
        self.path = path
        self.writer = writer
        self.stack = []

    def visit_scope(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_scope

    def visit_Call(self, node):
        name = getattr(node.func, 'attr', getattr(node.func, 'id', ''))
        kind = classify(node, name)
        if kind:
            if kind == 'catalog API' or kind == 'native dispatch':
                target = ', '.join(ast.unparse(arg) for arg in node.args[:3])
            else:
                target = ', '.join(ast.unparse(arg) for arg in node.args[:2])
            self.writer.writerow([self.path, node.lineno, '.'.join(self.stack),
                                  kind, ast.unparse(node.func), target[:200] or '—'])
        self.generic_visit(node)


def main():
    tracked = subprocess.check_output(['git', 'ls-files', '--', 'wepppy']).decode().splitlines()
    paths = [path for path in tracked if path.endswith('.py')]
    writer = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
    writer.writerow(['source', 'line', 'scope', 'evidence', 'call', 'leading_arguments'])
    counts = Counter()
    for path in paths:
        with tokenize.open(path) as handle:
            try:
                tree = ast.parse(handle.read(), filename=path)
            except SyntaxError:
                counts['unparsed'] += 1
                print('unparsed', path, file=sys.stderr)
                continue
        Visitor(Path(path), writer).visit(tree)
        counts['parsed'] += 1
    print(dict(counts), file=sys.stderr)


if __name__ == '__main__':
    main()
