"""Real temporary-Git controls for promoted binary binding; no model/build."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import final_pair_binding_v3 as binding
import final_pair_binding_v2 as previous


def run():
    checks=[]
    def git(root,*args):
        return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.STDOUT).strip()
    def reject(name,call):
        try:call()
        except (ValueError,FileNotFoundError):checks.append(name)
        else:raise AssertionError('Accepted '+name)
    with tempfile.TemporaryDirectory(prefix='pair-binding-v3-') as temp:
        root=Path(temp);native=root/'native';native.mkdir();pair=root/'pair';(pair/'candidate/src').mkdir(parents=True)
        for directory in ('src','fpm-src','tests','tools','release'):(native/directory).mkdir()
        for role in ('wepp','wepp_hill'):(native/'src'/role).write_bytes(b'old tracked binary\n')
        for directory in ('src','fpm-src','tests','tools'):(native/directory/'control.txt').write_text('committed source/control\n')
        git(native,'init','-b','test-binding');git(native,'add','.');git(native,'-c','user.name=Control','-c','user.email=control@example.invalid','commit','-m','temporary fixture')
        commit=git(native,'rev-parse','HEAD');branch=git(native,'branch','--show-current')
        binary=Path('/usr/bin/true').resolve();digest=binding.u.sha(binary);libraries=binding.u.runtime(binary)
        receipt=dict(passed=True,source_commit=commit,binaries={})
        for role,dated,kind in [('wepp','wepp_261029','watershed'),('wepp_hill','wepp_261029_hill','hillslope')]:
            for destination in (pair/'candidate/src'/role,native/'src'/role,native/'release'/dated):shutil.copy2(binary,destination)
            receipt['binaries']['candidate/'+role]=dict(sha256=digest,libraries=libraries)
            (native/'release'/(dated+'.json')).write_text(json.dumps(dict(binary_name=dated,binary_role=kind,source_branch=branch,source_commit=commit,sha256=digest)))
        receipt_path=pair/'receipt.json';receipt_path.write_text(json.dumps(receipt))
        result=binding.bind_pair(pair,native)
        assert result['source_commit']==commit and len(result['binaries'])==2
        checks.append('both tracked promoted binaries allowed with exact copy/runtime bindings')
        try:previous.bind_pair(pair,native)
        except subprocess.CalledProcessError:checks.append('frozen v2 reproduces promoted tracked binary rejection')
        else:raise AssertionError('Expected frozen v2 failure did not reproduce')
        git(native,'add','src/wepp','src/wepp_hill')
        binding.bind_pair(pair,native);checks.append('staged promoted binary paths retain all identity gates')
        git(native,'reset','HEAD','--','src/wepp','src/wepp_hill')
        assert set(git(native,'diff','--name-only','HEAD').splitlines())=={'src/wepp','src/wepp_hill'}
        for role in ('wepp','wepp_hill'):
            path=native/'src'/role;data=path.read_bytes();path.write_bytes(data+b'drift')
            reject(role+' promoted hash mismatch',lambda:binding.bind_pair(pair,native));path.write_bytes(data)
        for directory in ('src','fpm-src','tests','tools'):
            path=native/directory/'control.txt';original=path.read_text();path.write_text('changed\n')
            reject(directory+' tracked working source/control edit',lambda:binding.bind_pair(pair,native))
            git(native,'add',str(path.relative_to(native)))
            reject(directory+' staged source/control edit',lambda:binding.bind_pair(pair,native))
            git(native,'reset','HEAD','--',str(path.relative_to(native)));path.write_text(original)
            extra=native/directory/'new-untracked.txt';extra.write_text('not committed\n')
            reject(directory+' untracked input',lambda:binding.bind_pair(pair,native));extra.unlink()
        path=native/'src/wepp_extra';path.write_text('not an allowed basename\n');git(native,'add','src/wepp_extra')
        reject('binary prefix is not allowlisted',lambda:binding.bind_pair(pair,native));git(native,'reset','HEAD','--','src/wepp_extra');path.unlink()
        renamed=native/'src/wepp-renamed';(native/'src/wepp').rename(renamed)
        reject('renamed promoted product',lambda:binding.bind_pair(pair,native));renamed.rename(native/'src/wepp')
        release=native/'release/wepp_261029';data=release.read_bytes();release.write_bytes(data+b'drift')
        reject('release copy drift still rejected',lambda:binding.bind_pair(pair,native));release.write_bytes(data)
        bad=json.loads(json.dumps(receipt));bad['binaries']['candidate/wepp']['libraries']={};receipt_path.write_text(json.dumps(bad))
        reject('runtime library identity still rejected',lambda:binding.bind_pair(pair,native));receipt_path.write_text(json.dumps(receipt))
        meta_path=native/'release/wepp_261029.json';metadata=meta_path.read_text();bad=json.loads(metadata);bad['source_commit']='wrong';meta_path.write_text(json.dumps(bad))
        reject('sidecar source identity still rejected',lambda:binding.bind_pair(pair,native));meta_path.write_text(metadata)
        result=binding.bind_pair(pair,native);assert result['binaries']['wepp']==str(pair/'candidate/src/wepp')
        checks.append('restored real temporary repository passes')
    return dict(passed=True,count=len(checks),controls=checks,temporary_git_repository=True,model_or_build_execution=False,
                executable_fixture='/usr/bin/true used only as copy/hash/ldd input; never executed')

if __name__=='__main__':print(json.dumps(run(),indent=2))
