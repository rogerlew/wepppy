import os

from multiprocessing import Pool

from wepppy.soils.ssurgo import SurgoSoilCollection

from datetime import datetime


def load_mukeys():
    with open('mukeys.txt') as fp:
        return [v.strip() for v in fp.readlines()]
        
def build(args):
    mukeys = load_mukeys()
    
    j, ncpu = args
    for i in xrange(0, 1487):
        i0 = i*197
        iend = i0 + 197
        
        if (int(i) + int(j)) % ncpu != 0:
            continue
        
        _mukeys = mukeys[i0:iend]
        
        ssurgo_c = SurgoSoilCollection([int(m) for m in _mukeys])
        ssurgo_c.makeWeppSoils()
        
        for m in _mukeys:
            weppSoil = ssurgo_c.weppSoils.get(int(m), None)
            
            k = m[:3]
            
            if weppSoil is None:
                path = os.path.join('invalid', k)
                if not os.path.exists(path):
                    os.mkdir(path)
                
                with open(os.path.join(path, m), 'w') as fp:
                    fp.write(str(datetime.now()))
                    
            else:
                path = os.path.join('cache', k)
                if not os.path.exists(path):
                    os.mkdir(path)
                
                with open(os.path.join(path, '%s.sol' % m), 'w') as fp:
                    fp.write(weppSoil.build_file_contents())
             
if __name__ == "__main__":

    mukeys = load_mukeys()
    
    valid = []
    invalid = []
    unknown = []
    for m in mukeys:
        if os.path.exists(os.path.join('cache', m[:3], '%s.sol' % m)):
            valid.append(m)
            
        elif os.path.exists(os.path.join('invalid', m[:3], m)):
            invalid.append(m)
            
        else:
            unknown.append(m)
            
            
    print( 'valid\t', len(valid))
    print( 'invalid\t', len(invalid))
    print( 'unknown\t', len(unknown))
    print( 'total\t', len(valid) + len(invalid) + len(unknown))

#    if os.path.exists('cache'):
#        shutil.rmtree('cache')
        
#    if os.path.exists('invalid'):
#        shutil.rmtree('invalid')
        
#    os.mkdir('cache')
#    os.mkdir('invalid')
    
    #build([0,1])
    ncpu = 4
    pool = Pool(processes=ncpu)
    pool.map(build, [(i, ncpu) for i in range(ncpu)])
