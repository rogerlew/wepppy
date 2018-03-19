import array
import sys
import os
from bisect import bisect_left

class WeppSoil_db(object):
    def __init__(self, db_dir='./'):
        d_fn = _join(db_dir, 'mukeys.dat')
        m_fn = _join(db_dir, 'mukeys_mask.dat')

        n = os.stat(d_fn).st_size / 4
        m = os.stat(m_fn).st_size
        assert n == m, (n, m)

        print n
        self.mukeys = array.array('i')
        self.mukeys.fromfile(open(d_fn, 'rb'), n)
        self.mask = array.array('b')
        self.mask.fromfile(open(m_fn, 'rb'), n)
        
        print self.mukeys[:10]
        print self.mask[:10]
        print self.mask[0] == 1
        print self.mask[1] == 1

    def stat(self, m):
        a = self.mukeys
        x = int(m)
        i = bisect_left(a, x)
        if i != len(a) and a[i] == x:
            return self.mask[i] == 1
        return None

def stat2(m):
    if _exists(_join('cache', m[:3], '%s.sol' % m)):
        return True

    elif _exists(_join('invalid', m[:3], m)):
        return False
    else:
        return None
 
if __name__ == "__main__":
    from time import time
    from _1_build import load_mukeys
    mukeys = load_mukeys()
    
    t0 = time()
    weppsoil_db = WeppSoil_db()
    valid, invalid, unknown = [], [], []
    for m in mukeys:
        s = weppsoil_db.stat(m)
        if s == True:
            valid.append(m)
        elif s == False:
            invalid.append(m)
        else:
            unknown.append(m)
    print 'elapsed', time() - t0
    print 'valid', len(valid)
    print 'invalid', len(invalid)
    print 'unknown', len(unknown)
    
    
    sys.exit()
    t0 = time()
    states2 = []
    for m in mukeys:
        states2.append(stat2(m))
    print 'elapsed', time() - t0
