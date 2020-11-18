from os.path import exists as _exists

from enum import IntEnum

from pprint import pprint
"""
p1.cli                                             
  100         1
.23400E+05
  5    0.20000E-05 0.10000E-04 0.34500E-04 0.54500E-03 0.20000E-03
    0.00     0.00     0.00     0.00
NO EVENT      2    25      0.65587E+01 0.00000E+00
EVENT         3     8      0.10800E+05 0.11345E+00 0.63642E-01 0.27836E-02 0.65137E+02 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.10150E-01      0.31549E+01 0.00000E+00 0.34317E-02 0.33028E-02 0.13868E-01      0.24152E-01 0.36816E-02 0.70850E-01 0.68190E-01 0.28631E+00
SUBEVENT      2   152      0.91566E-05 0.21426E+00 0.00000E+00 0.00000E+00 0.15037E+02 0.00000E+00
"""

class PassEventType(IntEnum):
    NO_EVENT = 0
    EVENT = 1
    SUBEVENT = 2


class Pass:
    def __init__(self, fn):
        assert _exists(fn)

        with open(fn) as fp:
            lines = fp.readlines()

        wshcli = lines[0]
        nyr, byr = [int(v) for v in lines[1].split()]
        harea = float(lines[2])

        line3 = lines[3].split()
        npart = int(line3[0])
        dia = [float(v) for v in line3[1:]]
        assert len(dia) == npart

        srp, slfp, bfp, scp = [float(v) for v in lines[4].split()]

        events = []
        for i, line in enumerate(lines[5:]):
            if line.startswith('NO EVENT'):
                event = PassEventType.NO_EVENT
                year, day, gwbfv, gwdsv = line.split()[-4:]
                year = int(year)
                day = int(day)
                gwbfv = float(gwbfv)
                gwdsv = float(gwdsv)

                events.append(dict(event=event, year=year, day=day, gwbfv=gwbfv, gwdsv=gwdsv))

            elif line.startswith('EVENT   '):
                event = PassEventType.EVENT
                _line = line.split() + lines[i+6].split()

                year = int(_line[1])
                day = int(_line[2])
                dur = float(_line[3])      # (s)
                tcs = float(_line[4])      #  overland flow time of concentration (hr)
                oalpha = float(_line[5])   # overland flow alpha parameter (unitless)
                runoff = float(_line[6])   # (m)
                runvol = float(_line[7])   # (m^3)
                sbrunf = float(_line[8])
                sbrunv = float(_line[9])   # lateral flow (m^3)
                drainq = float(_line[10])  # drainage flux (m/day)
                drrunv = float(_line[11])
                peakro_vol = float(_line[12])  # (m^3/s)
                tdet = float(_line[13])    # total detachment (kg)
                tdep = float(_line[14])    # total deposition (kg)
                sedcon = [float(_line[15]), float(_line[16]), float(_line[17]), float(_line[18]), float(_line[19])]

                frcflw = float(_line[20])
                gwbfv = float(_line[21])
                gwdsv = float(_line[22])

                events.append(dict(event=event, year=year, day=day, dur=dur, tcs=tcs, oalpha=oalpha, runoff=runoff,
                                   runvol=runvol, sbrunf=sbrunf, sbrunv=sbrunv, drainq=drainq, drrunv=drrunv,
                                   peakro_vol=peakro_vol, tdet=tdet, tdep=tdep, sedcon=sedcon,  frcflw=frcflw, gwbfv=gwbfv, gwdsv=gwdsv))

            elif line.startswith('SUBEVENT'):
                event = PassEventType.SUBEVENT
                year, day, sbrunf, sbrunv, drainq, drrunv, gwbfv, gwdsv = line.split()[1:]
                year = int(year)
                day = int(day)
                sbrunf = float(sbrunf)
                sbrunv = float(sbrunf)
                drainq = float(drainq)
                drrunv = float(drrunv)
                gwbfv = float(gwbfv)
                gwdsv = float(gwdsv)

                events.append(dict(event=event, year=year, day=day, sbrunf=sbrunf, sbrunv=sbrunv, drainq=drainq, drrunv=drrunv, gwbfv=gwbfv, gwdsv=gwdsv))

        self.wshcli = wshcli
        self.nyr = nyr
        self.byr = byr
        self.harea = harea
        self.npart = npart
        self.dia = dia
        self.srp = srp
        self.slfp = slfp
        self.bfp = bfp
        self.scp = scp
        self.events = events


if __name__ == "__main__":
    fn = '/geodata/weppcloud_runs/undefeated-clue/wepp/output/H1.pass.dat'
    Pass(fn)
