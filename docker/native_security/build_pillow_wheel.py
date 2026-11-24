"""Build the owned Pillow wheel without changing its unrelated native codecs."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

PILLOW_URL = 'https://files.pythonhosted.org/packages/e6/99/fdf65cc539e266ab93546c261bdf98411fe165c6e4e13f9dbf597097192b/pillow-13.0.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'
PILLOW_SHA256 = '42d63be3af4f9b951b199b0a9d23365d37ab14687e6d77b74940432c8515c4ca'
BROTLI_COMMIT = 'db24a98aed38a16de78cc05ca15cdd8dc2a0d92d'
BROTLI_URL = 'https://codeload.github.com/google/brotli/tar.gz/' + BROTLI_COMMIT
BROTLI_SHA256 = '113b9685dfc14dd2f3360d077283266eec2fbdfb0fe3e5600f11be151da0d68e'
ALIASES = {'brotlicommon': 'libbrotlicommon-53534446.so.1.2.0',
           'brotlidec': 'libbrotlidec-7e5462ba.so.1.2.0'}
OLD_INFO = 'pillow-13.0.0.dist-info/'
NEW_INFO = 'pillow-13.0.0+wepp1.dist-info/'
WHEEL_NAME = 'pillow-13.0.0+wepp1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def download(url, destination, expected):
    with urllib.request.urlopen(url, timeout=120) as response, destination.open('wb') as target:
        shutil.copyfileobj(response, target)
    if sha256(destination.read_bytes()) != expected:
        raise RuntimeError('Native build input digest mismatch: ' + url)


def command(*args):
    return subprocess.check_output(args, text=True)


def elf_contract(path):
    dynamic = command('readelf', '-d', str(path))
    symbols = command('readelf', '--dyn-syms', '--wide', str(path))
    exports = []
    imports = []
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[4] in ('GLOBAL', 'WEAK') and fields[6] == 'UND':
            imports.append(fields[7])
        if len(fields) >= 8 and fields[4] in ('GLOBAL', 'WEAK') and fields[6] != 'UND':
            exports.append(fields[3:6] + [fields[7]] +
                           ([fields[2]] if fields[3] == 'OBJECT' else []))
    return {'loader': sorted(re.findall(r'\((NEEDED|SONAME|RPATH|RUNPATH)\).*?\[(.*?)\]', dynamic)),
            'exports': sorted(exports), 'imports': sorted(imports),
            'glibc_versions': sorted({tuple(map(int, version.split('.')))
                                      for version in re.findall(r'GLIBC_([\d.]+)', symbols)})}


def build_libraries(root, archive, original):
    with tarfile.open(archive) as source_archive:
        source_archive.extractall(root, filter='data')
    source = root / ('brotli-' + BROTLI_COMMIT)
    # Keep the existing private loader aliases. They are compatibility names,
    # not claims about the repaired library's source version or content hash.
    with (source / 'CMakeLists.txt').open('a') as cmake:
        for target, alias in ALIASES.items():
            output_name = alias.removeprefix('lib').removesuffix('.so.1.2.0')
            rpath = ' INSTALL_RPATH ""' if target == 'brotlicommon' else ''
            cmake.write(f'\nset_target_properties({target} PROPERTIES OUTPUT_NAME "{output_name}" '
                        f'VERSION "1.2.0" SOVERSION "1.2.0"{rpath})\n')
    build = root / 'build'
    subprocess.run(['cmake', '-S', str(source), '-B', str(build),
                    '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
                    '-DBROTLI_DISABLE_TESTS=ON', '-DCMAKE_C_FLAGS=-march=x86-64 -mtune=generic',
                    '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON', '-DCMAKE_INSTALL_RPATH=$ORIGIN',
                    '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,--no-as-needed -lm -Wl,--as-needed,--disable-new-dtags,-z,relro,-z,now'], check=True)
    subprocess.run(['cmake', '--build', str(build), '--parallel', '2', '--target',
                    'brotlidec', 'brotlicommon'], check=True)
    replacements = {}
    for alias in ALIASES.values():
        replacement = build / alias
        subprocess.run(['strip', '--strip-unneeded', str(replacement)], check=True)
        previous = root / ('upstream-' + alias)
        previous.write_bytes(original.read('pillow.libs/' + alias))
        old_contract, new_contract = elf_contract(previous), elf_contract(replacement)
        # Ubuntu's compiler adds these libc hardening calls; both predate the
        # retained GLIBC floor. Preserve them without permitting other drift.
        extra_imports = set(new_contract['imports']) - set(old_contract['imports'])
        missing_imports = set(old_contract['imports']) - set(new_contract['imports'])
        allowed_hardening = {'__memcpy_chk@GLIBC_2.3.4', '__stack_chk_fail@GLIBC_2.4'}
        if (any(old_contract[key] != new_contract[key] for key in ('loader', 'exports'))
                or missing_imports or not extra_imports <= allowed_hardening):
            raise RuntimeError('Brotli loader/export ABI changed: ' + alias)
        if any(version > (2, 27) for version in new_contract['glibc_versions']):
            raise RuntimeError('Rebuilt Brotli exceeds the retained manylinux_2_27 GLIBC floor')
        if re.search(r'x86-64-v[234]', command('readelf', '-n', str(replacement))):
            raise RuntimeError('Rebuilt Brotli requires an unqualified x86 ISA')
        replacements['pillow.libs/' + alias] = replacement.read_bytes()
    return replacements


def record_row(name, data):
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
    return [name, 'sha256=' + digest, str(len(data))]


def repack(original, destination, replacements):
    contents = {info.filename: (info, original.read(info)) for info in original.infolist()}
    for name, digest, length in csv.reader(io.StringIO(contents[OLD_INFO + 'RECORD'][1].decode())):
        if digest and record_row(name, contents[name][1])[1:] != [digest, length]:
            raise RuntimeError('Upstream Pillow RECORD mismatch: ' + name)
    metadata = contents[OLD_INFO + 'METADATA'][1]
    if metadata.count(b'Version: 13.0.0\n') != 1:
        raise RuntimeError('Unexpected Pillow metadata version')
    provenance = {'upstream_pillow_version': '13.0.0', 'owned_distribution_version': '13.0.0+wepp1',
                  'upstream_wheel_sha256': PILLOW_SHA256, 'brotli_source_version': '1.2.1',
                  'brotli_source_commit': BROTLI_COMMIT, 'brotli_source_sha256': BROTLI_SHA256,
                  'private_compatibility_aliases': {name: {'actual_sha256': sha256(data),
                     'actual_source_version': '1.2.1'} for name, data in replacements.items()},
                  'upstream_sboms': 'Retained as upstream input evidence; not a complete owned-output SBOM'}
    rows = []
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for name, (info, data) in contents.items():
            if name == OLD_INFO + 'RECORD':
                continue
            info.filename = name.replace(OLD_INFO, NEW_INFO)
            if name in replacements:
                data = replacements[name]
            if name == OLD_INFO + 'METADATA':
                data = data.replace(b'Version: 13.0.0\n', b'Version: 13.0.0+wepp1\n')
            output.writestr(info, data)
            rows.append(record_row(info.filename, data))
        name = NEW_INFO + 'wepppy-native-repair.json'
        data = (json.dumps(provenance, indent=2) + '\n').encode()
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        output.writestr(info, data)
        rows.append(record_row(name, data))
        record = io.StringIO()
        writer = csv.writer(record, lineterminator='\n')
        writer.writerows(rows)
        writer.writerow([NEW_INFO + 'RECORD', '', ''])
        info = zipfile.ZipInfo(NEW_INFO + 'RECORD', date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        output.writestr(info, record.getvalue())
    # PIL/_version.py and the native core must remain 13.0.0 together. Only the
    # distribution metadata gains the owned revision; every other codec stays.
    with zipfile.ZipFile(destination) as output:
        for name, (_, data) in contents.items():
            if '.so' in name and name not in replacements and output.read(name) != data:
                raise RuntimeError('Unrelated Pillow native member changed: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_directory', type=Path)
    args = parser.parse_args()
    if command('dpkg', '--print-architecture').strip() != 'amd64':
        raise SystemExit('Qualify this owned wheel for other architectures before building')
    args.output_directory.mkdir(parents=True, exist_ok=True)
    destination = args.output_directory / WHEEL_NAME
    with tempfile.TemporaryDirectory(prefix='wepppy-pillow-') as temporary:
        root = Path(temporary)
        wheel, archive = root / 'upstream.whl', root / 'brotli.tar.gz'
        download(PILLOW_URL, wheel, PILLOW_SHA256)
        download(BROTLI_URL, archive, BROTLI_SHA256)
        with zipfile.ZipFile(wheel) as original:
            repack(original, destination, build_libraries(root, archive, original))
    print(json.dumps({'wheel': str(destination), 'sha256': sha256(destination.read_bytes())}))


if __name__ == '__main__':
    main()
