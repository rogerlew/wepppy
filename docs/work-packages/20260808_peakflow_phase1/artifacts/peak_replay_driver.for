      program peak_replay
c     Process-isolated Phase 1 driver for the pinned APPMTH and HDRIVE.
      include 'pmxelm.inc'
      include 'pmxtim.inc'
      include 'pmxpln.inc'
      include 'cconsts.inc'
      include 'cdata3.inc'
      include 'chydrol.inc'
      include 'cintgrl.inc'
      include 'cpass1.inc'
      include 'cpass2.inc'
      include 'cpass3.inc'
      include 'cpass4.inc'
      include 'cprams1.inc'
      real alpha,xlen,runin,remin,effdur,appeak,hdpeak
      real fraction
      integer i

      read(*,*) alpha,m,xlen,runin,remin,effdur,ns
      if (ns.lt.1.or.ns+1.gt.mxtime) stop 2
      do 10 i=1,ns+1
        read(*,*) t(i),s(i)
   10 continue
      tstar=t(ns+1)
      si(1)=0.d0
      do 20 i=2,ns+1
        si(i)=si(i-1)+s(i-1)*(t(i)-t(i-1))
   20 continue
      len=xlen
      a1=m*alpha
      a2=m-1.0
      durexr=effdur
      durrun=effdur
      call appmth(runin,remin,xlen,alpha,m,effdur,appeak)
      call hdrive(alpha,m,xlen,runin,hdpeak)
      fraction=0.0
      if (runin.gt.0.0.and.nqt.gt.0) fraction=qtot(nqt)/xlen/runin
      write(*,1000) appeak,hdpeak,nqt,nq,fraction
 1000 format(2(es24.16e3,1x),2(i0,1x),es24.16e3)
      end
