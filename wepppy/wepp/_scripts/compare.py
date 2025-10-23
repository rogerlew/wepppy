

linux = open('loss_pw0_linux.txt').readlines()
linux = [L.strip() for L in linux]
linux = [L for L in linux if len(L) > 0]

windows = open('loss_pw0_windows.txt').readlines()
windows = [L.strip() for L in windows]
windows = [L for L in windows if len(L) > 0]

print(len(linux), len(windows))


def compare_tokens(x, y):
    try:
        _x = float(x)
        _y = float(y)

        if _x == _y:
            return True

        return _x * 0.8 < _y < _x * 1.2

    except:
        return x == y


def compare_row(L, W):

    _L = L.split()
    _W = W.split()

    if len(_L) != len(_W):
        print(len(_L) != len(_W))
        return False

    mask = [compare_tokens(x, y) for x, y in zip(_L, _W)]
    if not all(mask):
        print(mask)
        return False
    return True

fp = open('linux_windows_comparison_report.txt', 'w')

year = None
for i in range(len(linux)):
    L = linux[i]
    W = windows[i]

    if L.startswith('ANNUAL SUMMARY FOR WATERSHED IN YEAR'):
        year = L.split()[-1]

    if not compare_row(L, W):
        fp.write('{} {}\n'.format(year, i+1))
        fp.write('Linux:   ' + L + '\n')
        fp.write('Windows: ' + W + '\n\n')
