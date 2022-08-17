from glob import glob
import csv
import os

from os.path import split as _split

_lookup = {
    '3inslope.man': '3_RoadDesign.InslopeX_Traffic.LowOrHigh.man',
    '3outunr.man': '3_RoadDesign.OutslopeUnrutted_Traffic.LowOrHigh.man',
    '3outrut.man': '3_RoadDesign.OutslopeRutted_Traffic.LowOrHigh.man',
    '3outrut.man': '3_RoadDesign.OutslopeRutted_Traffic.LowOrHigh.man',
    '3inslopen.man': '3_RoadDesign.InslopeX_Traffic.None.man',
    '3outunrn.man': '3_RoadDesign.OutslopeUnrutted_Traffic.None.man',
    '3outrutn.man': '3_RoadDesign.OutslopeRutted_Traffic.None.man',
    '3outrutn.man': '3_RoadDesign.OutslopeRutted_Traffic.None.man',
}

_symlinks = {
  '3_RoadDesign.InslopeX_Traffic.LowOrHigh.man': (
    '3_RoadDesign.InslopeBare_Traffic.Low.man',
    '3_RoadDesign.InslopeBare_Traffic.High.man',
    '3_RoadDesign.InslopeVegetated_Traffic.Low.man',
    '3_RoadDesign.InslopeVegetated_Traffic.High.man',
   ),
  '3_RoadDesign.OutslopeUnrutted_Traffic.LowOrHigh.man': (
    '3_RoadDesign.OutslopeUnrutted_Traffic.Low.man',
    '3_RoadDesign.OutslopeUnrutted_Traffic.High.man',
   ),
  '3_RoadDesign.OutslopeRutted_Traffic.LowOrHigh.man': (
    '3_RoadDesign.OutslopeRutted_Traffic.Low.man',
    '3_RoadDesign.OutslopeRutted_Traffic.High.man',
   ),
  '3_RoadDesign.InslopeX_Traffic.None.man': (
    '3_RoadDesign.InslopeBare_Traffic.None.man',
    '3_RoadDesign.InslopeVegetated_Traffic.None.man',
   )
}

if __name__ == "__main__":
    os.chdir('../')
    man_fns = glob('og/*.man')

    for man_fn in man_fns:
       head, tail = _split(man_fn)
       if '200.man' == tail:
           continue

       new_fn = _lookup[tail]

       txt = open(man_fn).readlines()

       with open(new_fn, 'w') as fp:
           fp.write(''.join(txt[:-1791])) # remove last 1790 lines


    for target, links in _symlinks.items():
        for link in links:
            print(target, link)
            os.symlink(target, link)

