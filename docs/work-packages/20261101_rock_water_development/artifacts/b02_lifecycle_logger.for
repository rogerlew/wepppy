C     Original full-period lifecycle observer. Only model reads.
      subroutine b2lc(tag,yr,dy,ip,extra)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'pmxpnd.inc'
      include 'cwater.inc'
      include 'ccons.inc'
      include 'cwint.inc'
      include 'cparame.inc'
      include 'ccrpout.inc'
      character*(*) tag
      integer yr,dy,ip,k,ios,cy,cd,refreshed
      integer*8 seq
      double precision extra,v(16)
      logical first,enabled,sealed
      save first,enabled,sealed,seq,cy,cd,refreshed
      data first/.true./,enabled/.false./,sealed/.false./,seq/0/
      data cy/0/,cd/0/,refreshed/0/
      if(first)then
        inquire(file='b02_flux_windows.txt',exist=enabled)
        if(enabled)then
          open(975,file='b02-daily-lifecycle.txt',status='new',
     1      action='write',iostat=ios)
          if(ios.ne.0)stop 'B02 lifecycle destination exists'
          write(975,'(a)')'B2_LIFECYCLE_SCHEMA 1'
        endif
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'B02 lifecycle record after footer'
      if(tag.eq.'END')then
        write(975,'(a,1x,i18)')'B2_LIFECYCLE_END',seq
        close(975)
        sealed=.true.
        return
      endif
      if(tag.eq.'CLOSE')then
C       Both cache writers have completed before this caller.
        cy=yr
        cd=dy
        refreshed=1
      endif
      if(tag.eq.'WIN_GATE')then
        v=0.d0
        v(1)=extra
        v(2)=dble(snodpy(ip))
        v(3)=dble(frdp(ip))
        seq=seq+1
        write(975,9000)tag,seq,yr,dy,ip,0,cy,cd,refreshed,v
      else
        do k=1,nsl(ip)
          v(1)=dble(st(k,ip))
          v(2)=dble(frzw(k,ip))
          v(3)=dble(dg(k,ip))
          v(4)=dble(frozen(k,ip))
          v(5)=dble(thetdr(k,ip))
          v(6)=dble(thetfc(k,ip))
          v(7)=dble(ul(k,ip))
          v(8)=dble(fc(k))
          v(9)=dble(por(k,ip))
          v(10)=dble(coca(k,ip))
          v(11)=dble(cpm(k,ip))
          v(12)=dble(bd(k,ip))
          v(13)=dble(solthk(k,ip))
C         INIDAT initializes both caches; init WATBAL refreshes SOILW.
C         Observed closing refresh is separate from initialization.
          v(14)=dble(soilw(k,ip))
          v(15)=dble(soilf(k,ip))
          v(16)=dble(frdp(ip))
          seq=seq+1
          write(975,9000)tag,seq,yr,dy,ip,k,cy,cd,refreshed,v
        enddo
      endif
 9000 format(a,1x,i18,7(1x,i8),16(1x,es24.16e3))
      return
      end
