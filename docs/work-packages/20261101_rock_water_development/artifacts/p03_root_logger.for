C     P03 read-only root census and selected hourly layer states.
      subroutine p3fx(tag,yr,dy,ip,hr,layer,a,b,c,d,e,f,g,h)
      implicit none
      character*(*) tag
      integer yr,dy,ip,hr,layer,ios,n,k,wy(64),wd(64),ey,ed
      integer*8 seq
      double precision a,b,c,d,e,f,g,h
      logical first,enabled,sealed,selected
      save first,enabled,sealed,seq,n,wy,wd
      data first/.true./,enabled/.false./,sealed/.false./,seq/0/
      if(first)then
        inquire(file='p03_root.on',exist=enabled)
        if(enabled)then
          open(973,file='p03_windows.txt',status='old',
     1      action='read',iostat=ios)
          if(ios.ne.0)stop 'P03 windows unavailable'
          read(973,*,iostat=ios)n
          if(ios.ne.0.or.n.lt.1.or.n.gt.64)stop 'P03 windows count'
          do k=1,n
            read(973,*,iostat=ios)wy(k),wd(k)
            if(ios.ne.0)stop 'P03 window record'
            if(wy(k).lt.1.or.wd(k).lt.1.or.wd(k).gt.366)
     1        stop 'P03 invalid window date'
            if(k.gt.1)then
              if(wy(k).lt.wy(k-1))stop 'P03 reversed year'
              if(wy(k).eq.wy(k-1).and.wd(k).le.wd(k-1))
     1          stop 'P03 duplicate/reversed window day'
            endif
          enddo
          read(973,*,iostat=ios)ey,ed
          if(ios.ge.0)stop 'P03 extra window record'
          close(973)
          open(974,file='p03-root.txt',status='new',
     1      action='write',iostat=ios)
          if(ios.ne.0)stop 'P03 root destination exists'
          write(974,'(a)')'P3_ROOT_SCHEMA 1'
        endif
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'P03 root record after footer'
      if(tag.eq.'END')then
        write(974,'(a,1x,i18)')'P3_ROOT_END',seq
        close(974)
        sealed=.true.
        return
      endif
      if(tag(1:2).eq.'H_')then
        selected=.false.
        do k=1,n
          if(yr.eq.wy(k).and.dy.eq.wd(k))selected=.true.
        enddo
        if(.not.selected)return
      endif
      seq=seq+1
      write(974,9000)tag,seq,yr,dy,ip,hr,layer,a,b,c,d,e,f,g,h
 9000 format(a,1x,i18,5(1x,i8),8(1x,es24.16e3))
      return
      end

C     Caller validity: only after hourly WATBAL initialized layer state.
      subroutine p3state(tag,yr,dy,ip,hr)
      implicit none
      character*(*) tag
      integer yr,dy,ip,hr,k
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'pmxcrp.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      do k=1,nsl(ip)
        call p3fx(tag,yr,dy,ip,hr,k,
     1    dble(st(k,ip)),dble(frzw(k,ip)),
     1    dble(ul(k,ip)),dble(dg(k,ip)),
     1    dble(thetdr(k,ip)),dble(thetfc(k,ip)),
     1    dble(solthk(k,ip)),dble(frozen(k,ip)))
      enddo
      return
      end
