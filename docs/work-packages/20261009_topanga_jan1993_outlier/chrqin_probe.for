      program chrqin_probe
c     Actual production CHRQIN objects, captured scalar/component inputs.
      include 'pmxelm.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'pmxprt.inc'
      include 'pmxslp.inc'
      include 'pmxtim.inc'
      include 'pmxseg.inc'
      include 'pmxcsg.inc'
      include 'pmxchr.inc'
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'cchpek.inc'
      include 'cdata1.inc'
      include 'cdata3.inc'
      include 'chydrol.inc'
      include 'cslope.inc'
      include 'cstore.inc'
      include 'cstruc.inc'
      include 'cstruct.inc'
      include 'cchvar.inc'
      include 'cchpar.inc'
      include 'cchrt.inc'
      include 'cmixsrc.inc'
      include 'cupdate.inc'
      real probeq(0:mxtchr),vcase,rcase,pcase,scase,tcase
      real rscaled,acase,ucase,bc,dc,raw1,raw2,denom
      integer caseid,istart,ii,ierr
      read(*,*) caseid,vcase,rcase,pcase,scase,tcase
      ielmt=1
      nhtop(1)=1
      mixused(1)=.true.
      mixdata(1,1)=rcase
      mixdata(2,1)=pcase
      mixdata(3,1)=scase
      read(*,*) (mixdata(ii,1),ii=4,27)
      watdur(1)=tcase
      tmppkr(1)=pcase
      ntchr=144
      dtchr=600.
      mofapp=1
      rscaled=dble(vcase)*dble(rcase)/
     1 (dble(rcase)+dble(scase))
      acase=rscaled/(pcase*tcase)
      if(acase.lt.1.) then
      call eqroot(acase,ierr,ucase)
      bc=ucase/(tcase/2.67)
      dc=ucase/(tcase-tcase/2.67)
      raw1=pcase*exp(dc*(tcase/2.67-600.))
      raw2=pcase*exp(dc*(tcase/2.67-1200.))
      denom=(raw1+raw2-raw1)*600.
      write(*,100) 'OPERANDS',caseid,rscaled,pcase,acase,ucase
      write(*,100) 'RAW',caseid,raw1,raw2,denom,rscaled/denom
      else
        write(*,100) 'FLAT',caseid,rscaled,pcase,acase,tcase
      endif
      do istart=0,1
        probeq=0.
        call chrqin(vcase,probeq,istart,3)
        write(*,100) 'RESULT',istart,maxval(probeq),
     1    sum(probeq(1:ntchr))*600.,probeq(1),probeq(2)
      enddo
 100  format(a,1x,i5,4(1x,es20.10))
      end
