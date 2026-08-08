#!/usr/bin/env python3
"""Apply the Phase 1 observational trace to a copy of WEPP ``irs.for``.

The transformation is deliberately anchored to the pinned f24c957e source and
fails if any expected block is absent.  It never calls a second peak solver.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "ef521b23485b99eaed0f0f5fa402266a2324b8b70ed989e4f04e27a07e06d884"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected one instrumentation anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def instrument(source: str) -> str:
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    if source_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected irs.for SHA-256: {source_hash}")

    source = replace_once(
        source,
        """      real maxrun, surpls,drlast,durre
      integer ibpln, iepln, xnpln, i, apr, nstemp, kplane, jumpfg
      integer jmpfg2, k,it,ii,j,ipl,l
""",
        """      real maxrun, surpls,drlast,durre
      real pddur,pdremax,pdpost,pdadd
      integer ibpln, iepln, xnpln, i, apr, nstemp, kplane, jumpfg
      integer jmpfg2, k,it,ii,j,ipl,l,pdmode
      logical pdon
""",
    )
    source = replace_once(
        source,
        """              if(surpls.gt.1.0E-6) then
                if(durre.gt.0.0) then
""",
        """              inquire(file='peak_diag.on',exist=pdon)
              pddur = durre
              pdremax = remax(iplane)
              pdpost = 0.0
              pdadd = 0.0
              pdmode = 0
              if(surpls.gt.1.0E-6) then
                if (pdon) open(unit=97,file='peak_diag.csv',
     1               status='unknown',position='append')
                if(durre.gt.0.0) then
                pdmode = 1
                pdadd = surpls/durre
""",
    )
    source = replace_once(
        source,
        """                  if(s(ii).gt.1.e-10)then
                    if (ii.eq.1) then
""",
        """                  if(s(ii).gt.1.e-10)then
                    if (pdon) write(97,9101) year,sdate,iplane,ii,
     1                    t(ii),t(ii+1),s(ii)
                    if (ii.eq.1) then
""",
    )
    source = replace_once(
        source,
        """                else
                    durre = tr(nf)-tr(1)
""",
        """                else
                    pdmode = 2
                    durre = tr(nf)-tr(1)
""",
    )
    source = replace_once(
        source,
        """                    if (durre.eq.0.0) durre = 86400.0
cd    End adding.
c
                    s(1) = surpls/durre
""",
        """                    if (durre.eq.0.0) then
                      durre = 86400.0
                      pdmode = 3
                    endif
cd    End adding.
c
                    pdadd = surpls/durre
                    s(1) = surpls/durre
""",
    )
    source = replace_once(
        source,
        """                call rdat(nowcrp(iplane))
c
                alphay(iplane) = alpha(iplane)
""",
        """                call rdat(nowcrp(iplane))
c
                if (pdon) then
                  pdpost = 0.0
                  do 934 ii = 1,ns
                    pdpost = max(pdpost,real(s(ii)))
  934             continue
                  write(97,9100) year,sdate,iplane,runoff(iplane),
     1              surpls,pddur,durre,pdremax,pdpost,pdadd,tp(2),
     1              alpha(iplane),m,efflen(iplane),ns,pdmode
                  do 937 ii = 1,ns+1
                    write(97,9102) year,sdate,iplane,ii,t(ii),s(ii)
  937             continue
                  close(97)
                endif
c
                alphay(iplane) = alpha(iplane)
""",
    )
    source = replace_once(
        source,
        """          if (peakro(kplane).lt.3.6e-8) peakro(kplane) = 3.63e-8
c
""",
        """          if (pdon) then
            open(unit=97,file='peak_diag.csv',status='unknown',
     1           position='append')
            if (tp(2).gt.0.0) then
              write(97,9103) year,sdate,kplane,'HDRIVE',peakro(kplane)
            else
              write(97,9103) year,sdate,kplane,'APPMTH',peakro(kplane)
            endif
            close(97)
          endif
c
          if (peakro(kplane).lt.3.6e-8) peakro(kplane) = 3.63e-8
c
""",
    )
    source = replace_once(
        source,
        """c
      return
      end
""",
        """c
 9100 format('SCALAR,',i0,',',i0,',',i0,',',11(es24.16e3,','),
     1       i0,',',i0)
 9101 format('PRE,',i0,',',i0,',',i0,',',i0,',',
     1       3(es24.16e3,:,','))
 9102 format('POST,',i0,',',i0,',',i0,',',i0,',',
     1       2(es24.16e3,:,','))
 9103 format('RESULT,',i0,',',i0,',',i0,',',a,',',es24.16e3)
c
      return
      end
""",
    )
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    rendered = instrument(args.source.read_text())
    args.destination.write_text(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
