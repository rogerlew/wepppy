"""Prove dated/U9a ELF equivalence without modifying either input binary."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

RAW = Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
REPO = Path('/workdir/wepp-forest-release-20261009')
ARTIFACTS = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def elf(path):
    data = path.read_bytes()
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    assert h[0][:6] == b'\x7fELF\x02\x01', path
    table = [struct.unpack_from('<IIQQQQIIQQ', data, h[6] + i * h[11])
             for i in range(h[12])]
    names = table[h[13]]
    strings = data[names[4]:names[4] + names[5]]
    sections = {}
    for s in table:
        name = strings[s[0]:].split(b'\0', 1)[0].decode()
        sections[name] = dict(type=s[1], flags=s[2], address=s[3], size=s[5],
                              link=s[6], info=s[7], alignment=s[8], entry_size=s[9],
                              sha256=None if s[1] == 8 else digest(data[s[4]:s[4]+s[5]]))
    programs = [struct.unpack_from('<IIQQQQQQ', data, h[5] + i*h[9])
                for i in range(h[10])]
    return data, h, sections, programs


def main():
    stage = RAW / '261029-r2-elf-equivalence'
    stage.mkdir(exist_ok=False)
    results = {}
    for candidate_name, release_name in [('wepp', 'wepp_261029'),
                                         ('wepp_hill', 'wepp_261029_hill')]:
        candidate = RAW / 'U9a-build/src' / candidate_name
        release = REPO / 'release' / release_name
        left, lh, ls, lp = elf(candidate)
        right, rh, rs, rp = elf(release)
        assert lp == rp, (release_name, 'program/load header drift')
        assert lh[1:6] == rh[1:6] and lh[7:11] == rh[7:11]
        assert set(ls) == set(rs), (release_name, 'section inventory drift')
        differing = {name: {'candidate': ls[name], 'dated': rs[name]}
                     for name in ls if ls[name] != rs[name]}
        assert all(name.startswith('.debug_') or name == '.note.gnu.build-id'
                   for name in differing), (release_name, list(differing))
        allocated = {name: section for name, section in ls.items()
                     if section['flags'] & 2 and name != '.note.gnu.build-id'}
        assert all(rs[name] == section for name, section in allocated.items())
        normalized = []
        commands = []
        for label, path in [('candidate', candidate), ('dated', release)]:
            target = stage / (release_name + '.' + label)
            command = ['objcopy', '--strip-debug', '--remove-section=.note.gnu.build-id',
                       str(path), str(target)]
            subprocess.run(command, check=True)
            commands.append(command)
            normalized.append(target.read_bytes())
        assert normalized[0] == normalized[1], (release_name, 'normalized binary drift')
        results[release_name] = {
            'candidate_sha256': digest(left), 'dated_sha256': digest(right),
            'full_file_identical': left == right,
            'normalized_file_identical': True,
            'normalized_sha256': digest(normalized[0]),
            'all_program_headers_identical': True,
            'program_headers': lp,
            'allocated_sections_except_build_id': allocated,
            'differing_sections': differing,
            'normalization_commands': commands,
            'interpretation': 'Exact code/data/layout equivalence. Differences limited to non-executable DWARF debug metadata and GNU build ID; source paths are not normalized in originals.',
        }
    receipt = dict(script_sha256=digest(Path(__file__).read_bytes()),
                   objcopy_version=subprocess.check_output(['objcopy','--version'],text=True).splitlines()[0],
                   binaries=results)
    (ARTIFACTS / 'native-dated-equivalence.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({name: {key: d[key] for key in ['candidate_sha256', 'dated_sha256',
                     'full_file_identical', 'normalized_file_identical']}
                     for name, d in results.items()}, indent=2))


if __name__ == '__main__':
    main()
