"""Retain why the dated build cannot inherit U9a's binary gates silently."""
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import os

ARTIFACTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('comparison', ARTIFACTS / 'compare_native_release_elf.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def functions(data, header):
    table = [struct.unpack_from('<IIQQQQIIQQ', data, header[6]+i*header[11])
             for i in range(header[12])]
    result = {}
    for section in table:
        if section[1] != 2:
            continue
        names = table[section[6]]
        strings = data[names[4]:names[4]+names[5]]
        for offset in range(section[4], section[4]+section[5], section[9]):
            name, info, _, index, address, size = struct.unpack_from('<IBBHQQ', data, offset)
            if info & 15 != 2 or size == 0 or index >= len(table):
                continue
            target = table[index]
            start = target[4]+address-target[3]
            name = strings[name:].split(b'\0',1)[0].decode()
            result[(name,address,size)] = comparison.digest(data[start:start+size])
    return result


def main():
    binaries = {}
    for cn, rn in [('wepp','wepp_261029'),('wepp_hill','wepp_261029_hill')]:
        a,ah,asec,ap = comparison.elf(comparison.RAW/'U9a-build/src'/cn)
        b,bh,bsec,bp = comparison.elf(comparison.REPO/'release'/rn)
        af,bf = functions(a,ah),functions(b,bh)
        differences = [{'name': k[0], 'address': k[1], 'size': k[2]}
                       for k in af if af[k] != bf.get(k)]
        assert set(af) == set(bf) and not differences
        for name in ['.rodata','.data','.bss','.got','.got.plt','.eh_frame','.eh_frame_hdr']:
            assert asec[name] == bsec[name], name
        binaries[rn] = dict(candidate_sha256=comparison.digest(a), dated_sha256=comparison.digest(b),
                            identical_function_bodies=len(af), function_body_differences=differences,
                            same_readonly_mutable_and_unwind_sections=True,
                            program_headers_equal=ap==bp,
                            differing_sections={n: {'candidate':asec[n], 'dated':bsec[n]}
                                                for n in asec if asec[n]!=bsec[n]},
                            decision='Do not claim exact executable/loaded-image equivalence. Revalidate actual system pair.')
    tools = {}
    for label,path in [('inherited',os.environ['PATH']),('dated','/usr/bin:/bin:'+os.environ['PATH'])]:
        tools[label] = {}
        for name in ['as','ld','objcopy']:
            binary=shutil.which(name,path=path)
            tools[label][name]={'path':binary,'version':subprocess.check_output([binary,'--version'],text=True).splitlines()[0]}
    result=dict(script_sha256=comparison.digest(Path(__file__).read_bytes()), binaries=binaries,
                toolchain=tools, cause='Absolute /usr/bin/gfortran does not pin PATH-resolved assembler/linker. U9a inherited binutils 2.46.1; dated staging selects system binutils 2.42.',
                observed_code_difference='objdump shows reordered inter-function NOP padding. All sized function bodies and their addresses are byte-identical.',
                loader_difference='GNU note placement, load/program headers, dynamic metadata addresses, and weak __gmon_start__ version local/global differ. These are not DWARF-only differences.',
                acceptance='Fresh native, Roads, Disturbed and Cedar gates on dated system pair required; original candidate untouched.')
    (ARTIFACTS/'native-toolchain-drift.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({n:d['identical_function_bodies'] for n,d in binaries.items()}))


if __name__=='__main__':main()
