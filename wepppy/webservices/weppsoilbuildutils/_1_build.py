import os
import sys
import shutil

from multiprocessing import Pool
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from soils.ssurgo import SurgoMap, SurgoSoilCollection

from datetime import datetime
from glob import glob
from pprint import pprint


def load_mukeys():
    with open('mukeys.txt') as fp:
        return [v.strip() for v in fp.readlines()]
        
def build(args):
    mukeys = load_mukeys()
    
    j, ncpu = args
    for i in range(0, 1487):
        i0 = i*197
        iend = i0 + 197
        
        if (int(i) + int(j)) % ncpu != 0:
            continue
        
        print(i,)
        _mukeys = mukeys[i0:iend]
        
        ssurgo_c = SurgoSoilCollection([int(m) for m in _mukeys])
        ssurgo_c.makeWeppSoils()
        
        for m in _mukeys:
            weppSoil = ssurgo_c.weppSoils.get(int(m), None)
            
            k = m[:3]
            
            if weppSoil is None:
                path = _join('invalid', k)
                if not _exists(path):
                    os.mkdir(path)
                
                with open(_join(path, m), 'w') as fp:
                    fp.write(str(datetime.now()))
                    
            else:
                path = _join('cache', k)
                if not _exists(path):
                    os.mkdir(path)
                
                with open(_join(path, '%s.sol' % m), 'w') as fp:
                    fp.write(weppSoil.build_file_contents())
             
if __name__ == "__main__":

    mukeys = load_mukeys()
    
    valid = []
    invalid = []
    unknown = []
    for m in mukeys:
        if _exists(_join('cache', m[:3], '%s.sol' % m)):
            valid.append(m)
            
        elif _exists(_join('invalid', m[:3], m)):
            invalid.append(m)
            
        else:
            unknown.append(m)
            
            
    print 'valid\t', len(valid)
    print 'invalid\t', len(invalid)
    print 'unknown\t', len(unknown)
    print 'total\t', len(valid) + len(invalid) + len(unknown)

    sys.exit()
    if _exists('cache'):
        shutil.rmtree('cache')
        
    if _exists('invalid'):
        shutil.rmtree('invalid')
        
    os.mkdir('cache')
    os.mkdir('invalid')
    
    #build([0,1])
    ncpu = 47
    pool = Pool(processes=ncpu)
    pool.map(build, [(i, ncpu) for i in range(ncpu)])