      program frozen_driver
c     Authored research driver; calls the complete unchanged native FRWATC.
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      integer mode1,mode2,j,stage,ip,il,jf,inactive_errors
      real nominalp,delta,liquid,ice,uf
      iplane=1
      year=1
      sdate=1
      nsl=0
      nsl(1)=1
      nfine=0
      dg=-777.
      thetdr=-777.
      ul=-777.
      st=-777.
      yst=-777.
      frozen=-777.
      frzw=-777.
      nwfrzz=-777.
      soilw=-777.
      saxfc=-777.
      slsw=-777.
      slsic=-777.
      slfsd=-777.
      read(*,*) nfine(1),mode1,mode2,delta
      read(*,*) dg(1,1),thetdr(1,1),nominalp,nwfrzz(1,1),saxfc(1,1)
      if(nfine(1).lt.1.or.nfine(1).gt.2) stop 2
      do j=1,nfine(1)
        read(*,*) slfsd(j,1,1),slsw(j,1,1),slsic(j,1,1)
      enddo
      frozen(1,1)=0.
      liquid=nwfrzz(1,1)
      ice=0.
      do j=1,nfine(1)
        frozen(1,1)=frozen(1,1)+slfsd(j,1,1)
        uf=dg(1,1)/nfine(1)-slfsd(j,1,1)
        liquid=liquid+slsw(j,1,1)*uf
        ice=ice+slsic(j,1,1)
      enddo
      ul(1,1)=(nominalp-thetdr(1,1))*dg(1,1)
      st(1,1)=liquid-thetdr(1,1)*(dg(1,1)-frozen(1,1))
      yst(1,1)=st(1,1)
      frzw(1,1)=ice-thetdr(1,1)*frozen(1,1)
      soilw(1,1)=liquid
      call snapshot(0)
      if(mode1.eq.1) st(1,1)=st(1,1)+delta
      call snapshot(1)
      call frwatc(mode1)
      call snapshot(2)
      if(mode2.ge.0) then
        call frwatc(mode2)
        call snapshot(3)
      endif
      inactive_errors=0
      do ip=1,mxplan
        do il=1,mxnsl
          if(ip.ne.1.or.il.ne.1) then
            if(st(il,ip).ne.-777..or.yst(il,ip).ne.-777..or.
     1       ul(il,ip).ne.-777..or.thetdr(il,ip).ne.-777..or.
     1       dg(il,ip).ne.-777..or.nwfrzz(il,ip).ne.-777..or.
     1       frozen(il,ip).ne.-777..or.frzw(il,ip).ne.-777..or.
     1       soilw(il,ip).ne.-777..or.saxfc(il,ip).ne.-777.)
     1       inactive_errors=inactive_errors+1
          endif
          do jf=1,10
            if(ip.ne.1.or.il.ne.1.or.jf.gt.nfine(1)) then
              if(slsw(jf,il,ip).ne.-777..or.
     1         slsic(jf,il,ip).ne.-777..or.
     1         slfsd(jf,il,ip).ne.-777.)
     1         inactive_errors=inactive_errors+1
            endif
          enddo
        enddo
      enddo
      write(*,'(a,1x,i0)') 'INACTIVE_ERRORS',inactive_errors
      write(*,'(a,4(1x,es24.16))') 'OUTSIDE',st(2,1),
     1 slsw(3,1,1),slfsd(3,1,1),nwfrzz(2,1)
      contains
      subroutine snapshot(stage)
      integer stage,k
      write(*,'(a,1x,i0,1x,i0,10(1x,es24.16))')
     1 'STATE',stage,nfine(1),dg(1,1),thetdr(1,1),ul(1,1),
     1 saxfc(1,1),frozen(1,1),frzw(1,1),nwfrzz(1,1),
     1 st(1,1),yst(1,1),soilw(1,1)
      do k=1,nfine(1)
        write(*,'(a,1x,i0,1x,i0,4(1x,es24.16))')
     1 'FINE',stage,k,slfsd(k,1,1),slsw(k,1,1),slsic(k,1,1),
     1 dg(1,1)/nfine(1)-slfsd(k,1,1)
      enddo
      end subroutine
      end program
