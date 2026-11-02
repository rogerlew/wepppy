C     Original selected-day observer. No native state assignments.
      subroutine b2fx(tag,yr,dy,ip,focus,layer,a,b,c,d,e,f,g,h,q,r)
      implicit none
      character*(*) tag
      integer yr,dy,ip,focus,layer,n,k,ios,wy(64),wd(64),ey,ed
      integer*8 seq
      double precision a,b,c,d,e,f,g,h,q,r
      logical first,enabled,sealed,selected
      save first,enabled,sealed,seq,n,wy,wd
      data first/.true./,enabled/.false./,sealed/.false./,seq/0/
      if(first)then
        inquire(file='b02_flux_windows.txt',exist=enabled)
        if(enabled)then
          open(976,file='b02_flux_windows.txt',status='old',
     1      action='read',iostat=ios)
          if(ios.ne.0)stop 'B02 flux windows unavailable'
          read(976,*,iostat=ios)n
          if(ios.ne.0.or.n.lt.1.or.n.gt.64)
     1      stop 'B02 flux window count'
          do k=1,n
            read(976,*,iostat=ios)wy(k),wd(k)
            if(ios.ne.0)stop 'B02 flux window record'
            if(wy(k).le.0.or.wd(k).lt.1.or.wd(k).gt.366)
     1        stop 'B02 flux invalid date'
            if(k.gt.1)then
              if(wy(k).lt.wy(k-1))stop 'B02 flux reversed date'
              if(wy(k).eq.wy(k-1).and.wd(k).le.wd(k-1))
     1          stop 'B02 flux duplicate date'
            endif
          enddo
          read(976,*,iostat=ios)ey,ed
          if(ios.ge.0)stop 'B02 flux extra window record'
          close(976)
          open(977,file='b02-daily-flux.txt',status='new',
     1      action='write',iostat=ios)
          if(ios.ne.0)stop 'B02 flux destination exists'
          write(977,'(a)')'B2_FLUX_SCHEMA 1'
        endif
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'B02 flux record after footer'
      if(tag.eq.'END')then
        write(977,'(a,1x,i18)')'B2_FLUX_END',seq
        close(977)
        sealed=.true.
        return
      endif
      selected=.false.
      do k=1,n
        if(yr.eq.wy(k).and.dy.eq.wd(k))selected=.true.
      enddo
      if(.not.selected)return
      seq=seq+1
      write(977,9000)tag,seq,yr,dy,ip,focus,layer,a,b,c,d,e,f,g,h,q,r
 9000 format(a,1x,i18,5(1x,i8),10(1x,es24.16e3))
      return
      end

C     Complete live layer state; called only inside actual daily WATBAL.
C     PURK calls occur within that same initialized daily invocation.
      subroutine b2fs(tag,yr,dy,ip,focus,extra)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'ccons.inc'
      include 'cwint.inc'
      character*(*) tag
      integer yr,dy,ip,focus,k
      double precision extra
      do k=1,nsl(ip)
        if(tag.eq.'OUTPUT')then
          call b2fx(tag,yr,dy,ip,focus,k,dble(soilw(k,ip)),extra,
     1      dble(soilf(k,ip)),0.d0,0.d0,0.d0,0.d0,0.d0,0.d0,0.d0)
        else
          call b2fx(tag,yr,dy,ip,focus,k,dble(st(k,ip)),
     1      dble(frzw(k,ip)),dble(ul(k,ip)),dble(fc(k)),
     1      dble(dg(k,ip)),dble(frozen(k,ip)),dble(thetdr(k,ip)),
     1      dble(coca(k,ip)),dble(solthk(k,ip)),dble(hk(k)))
        endif
      enddo
      return
      end
