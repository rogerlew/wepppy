"""Exercise matched candidate roles through actual configured application runners."""
from pathlib import Path
import argparse,hashlib,json,os
from wepp_runner.wepp_runner import get_linux_wepp_bin_role_paths,run_hillslope,run_watershed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path);parser.add_argument('--binary',default='wepp_261029');args=parser.parse_args()
    root=args.root;binary=args.binary
    watershed,hill=map(Path,get_linux_wepp_bin_role_paths(binary))
    inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'runs').iterdir()}
    hills=run_hillslope(1,str(root/'runs'),wepp_bin=binary,timeout=180,timeout_retries=0)
    assert hills[0],hills
    result=run_watershed(str(root/'runs'),wepp_bin=binary)
    assert result,result
    outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'output').iterdir()}
    assert 'loss_pw0.txt' in outputs and 'H1.pass.dat' in outputs
    (root/'receipt.json').write_text(json.dumps({'uid':os.getuid(),'gid':os.getgid(),
       'roles':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [watershed,hill]},
       'inputs':inputs,'outputs':outputs,'hillslope':hills,'watershed':result},indent=2)+'\n')
    print('Actual matched hill/watershed runner workflow PASS')


if __name__=='__main__': main()
