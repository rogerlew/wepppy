      program reset_driver
c     Authored harness; complete unchanged FRWATC is linked separately.
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
      integer rs_seq,rs_i,rs_j,rs_ip,rs_il,rs_jf,rs_errors
      real rs_p,rs_liquid,rs_ice,rs_u,rs_st,rs_yst
      iplane=1
      year=1
      sdate=1
      nsl=0
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
      read(*,*)nsl(1),rs_seq
      if(nsl(1).lt.1.or.nsl(1).gt.3)stop 2
      if(rs_seq.ne.1.and.rs_seq.ne.2)stop 3
      do rs_i=1,nsl(1)
        read(*,*)nfine(rs_i),dg(rs_i,1),thetdr(rs_i,1),rs_p,
     1   nwfrzz(rs_i,1),saxfc(rs_i,1),rs_st,rs_yst
        if(nfine(rs_i).lt.1.or.nfine(rs_i).gt.2)stop 4
        do rs_j=1,nfine(rs_i)
          read(*,*)slfsd(rs_j,rs_i,1),slsw(rs_j,rs_i,1),
     1     slsic(rs_j,rs_i,1)
        enddo
        frozen(rs_i,1)=0.
        rs_liquid=nwfrzz(rs_i,1)
        rs_ice=0.
        do rs_j=1,nfine(rs_i)
          frozen(rs_i,1)=frozen(rs_i,1)+slfsd(rs_j,rs_i,1)
          rs_u=dg(rs_i,1)/nfine(rs_i)-slfsd(rs_j,rs_i,1)
          rs_liquid=rs_liquid+slsw(rs_j,rs_i,1)*rs_u
          rs_ice=rs_ice+slsic(rs_j,rs_i,1)
        enddo
        ul(rs_i,1)=(rs_p-thetdr(rs_i,1))*dg(rs_i,1)
        st(rs_i,1)=rs_liquid-thetdr(rs_i,1)*
     1   (dg(rs_i,1)-frozen(rs_i,1))
        yst(rs_i,1)=st(rs_i,1)
        frzw(rs_i,1)=rs_ice-thetdr(rs_i,1)*frozen(rs_i,1)
        soilw(rs_i,1)=rs_liquid
        if(rs_st.ne.-888.)st(rs_i,1)=rs_st
        if(rs_yst.ne.-888.)yst(rs_i,1)=rs_yst
      enddo
      call rs_snapshot(0)
      if(rs_seq.eq.1)then
        call frwatc(1)
        call rs_snapshot(1)
      else
        call frwatc(0)
        call rs_snapshot(1)
        st(1:nsl(1),1)=0.
        call rs_snapshot(2)
        call frwatc(1)
        call rs_snapshot(3)
        call frwatc(1)
        call rs_snapshot(4)
      endif
      rs_errors=0
      do rs_ip=1,mxplan
        do rs_il=1,mxnsl
          if(rs_ip.ne.1.or.rs_il.gt.nsl(1))then
            if(st(rs_il,rs_ip).ne.-777..or.
     1       yst(rs_il,rs_ip).ne.-777..or.
     1       ul(rs_il,rs_ip).ne.-777..or.
     1       thetdr(rs_il,rs_ip).ne.-777..or.
     1       dg(rs_il,rs_ip).ne.-777..or.
     1       nwfrzz(rs_il,rs_ip).ne.-777..or.
     1       frozen(rs_il,rs_ip).ne.-777..or.
     1       frzw(rs_il,rs_ip).ne.-777..or.
     1       soilw(rs_il,rs_ip).ne.-777..or.
     1       saxfc(rs_il,rs_ip).ne.-777.)rs_errors=rs_errors+1
          endif
          do rs_jf=1,10
            if(rs_ip.ne.1.or.rs_il.gt.nsl(1).or.
     1       rs_jf.gt.nfine(rs_il))then
              if(slsw(rs_jf,rs_il,rs_ip).ne.-777..or.
     1         slsic(rs_jf,rs_il,rs_ip).ne.-777..or.
     1         slfsd(rs_jf,rs_il,rs_ip).ne.-777.)
     1         rs_errors=rs_errors+1
            endif
          enddo
        enddo
      enddo
      write(*,'(a,1x,i0)')'INACTIVE_ERRORS',rs_errors
      contains
      subroutine rs_snapshot(rs_stage)
      integer rs_stage,rs_l,rs_f
      do rs_l=1,nsl(1)
        write(*,9000)'C',rs_stage,rs_l,nfine(rs_l),
     1   dg(rs_l,1),thetdr(rs_l,1),ul(rs_l,1),saxfc(rs_l,1),
     1   frozen(rs_l,1),frzw(rs_l,1),nwfrzz(rs_l,1),
     1   st(rs_l,1),yst(rs_l,1),soilw(rs_l,1)
        do rs_f=1,nfine(rs_l)
          write(*,9010)'F',rs_stage,rs_l,rs_f,
     1     slfsd(rs_f,rs_l,1),slsw(rs_f,rs_l,1),
     1     slsic(rs_f,rs_l,1),
     1     dg(rs_l,1)/nfine(rs_l)-slfsd(rs_f,rs_l,1)
        enddo
      enddo
 9000 format(a,3(1x,i0),10(1x,es24.16e3))
 9010 format(a,3(1x,i0),4(1x,es24.16e3))
      end subroutine
      end program
