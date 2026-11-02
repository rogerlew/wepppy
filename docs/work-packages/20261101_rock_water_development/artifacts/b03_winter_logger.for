C     Original finite-window writer observer. No model assignments.
      subroutine b3open
      implicit none
      include 'b03_winter_context.inc'
      logical first,exists
      integer ios,k
      save first
      data first/.true./
      if(.not.first)return
      first=.false.
      b3on=0
      b3sel=0
      b3count=0
      b3pending=0
      b3seq=0
      b3cseq=0
      b3yr=0
      b3day=0
      b3ip=0
      b3hr=0
      inquire(file='b03_winter_windows.txt',exist=exists)
      if(.not.exists)return
      open(973,file='b03_winter_windows.txt',status='old',
     1 action='read',iostat=ios)
      if(ios.ne.0)stop 'B03 missing window input'
      read(973,*,iostat=ios)b3count
      if(ios.ne.0.or.b3count.lt.1.or.b3count.gt.64)
     1 stop 'B03 window count'
      do k=1,b3count
        read(973,*,iostat=ios)b3ys(k),b3ds(k)
        if(ios.ne.0)stop 'B03 incomplete window'
      enddo
      close(973)
      open(971,file='b03-winter-writers.txt',status='new',
     1 action='write',iostat=ios)
      if(ios.ne.0)stop 'B03 detail destination exists'
      open(972,file='b03-winter-census.txt',status='new',
     1 action='write',iostat=ios)
      if(ios.ne.0)stop 'B03 census destination exists'
      write(971,'(a)')'B3_DETAIL_SCHEMA 1'
      write(972,'(a)')'B3_CENSUS_SCHEMA 1'
      b3on=1
      end

      subroutine b3begin(yr,dy,ip,hr)
      implicit none
      include 'b03_winter_context.inc'
      integer yr,dy,ip,hr,k
      call b3open
      if(b3on.eq.0)return
      if(b3pending.ne.0)stop 'B03 unresolved writer'
      b3yr=yr
      b3day=dy
      b3ip=ip
      b3hr=hr
      b3sel=0
      do k=1,b3count
        if(yr.eq.b3ys(k).and.dy.eq.b3ds(k))b3sel=1
      enddo
      call b3snap('FROSTN_PRE',1,0)
      end

      subroutine b3snap(tag,mode,code)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'csaxp.inc'
      include 'b03_winter_context.inc'
      character*(*) tag
      integer mode,code,i,j,n
      double precision v(10)
      if(b3on.eq.0)return
      b3cseq=b3cseq+1
      write(972,9000)'C',tag,b3cseq,b3yr,b3day,b3ip,b3hr,
     1 code,mode
      if(b3sel.eq.0)return
      if(b3pending.ne.0)stop 'B03 snapshot inside assignment'
      b3seq=b3seq+1
      if(nsl(b3ip).lt.1.or.nsl(b3ip).gt.mxnsl)
     1 stop 'B03 coarse bounds'
      write(971,9001)'H',tag,b3seq,b3yr,b3day,b3ip,b3hr,
     1 code,mode,nsl(b3ip)
      if(mode.eq.0)return
      write(971,9002)'G',b3seq,dble(frdp(b3ip)),
     1 dble(thdp(b3ip)),dble(watpdg(b3ip)),dble(watbtm(b3ip))
      do i=1,nsl(b3ip)
        n=0
        if(mode.eq.2)then
          n=nfine(i)
          if(n.lt.1.or.n.gt.10)stop 'B03 fine bounds'
        endif
        v(1)=dble(st(i,b3ip))
        v(2)=dble(frzw(i,b3ip))
        v(3)=dble(dg(i,b3ip))
        v(4)=dble(frozen(i,b3ip))
        v(5)=dble(thetdr(i,b3ip))
        v(6)=dble(ul(i,b3ip))
        v(7)=dble(soilw(i,b3ip))
        v(8)=dble(yst(i,b3ip))
        v(9)=dble(nwfrzz(i,b3ip))
        v(10)=dble(saxfc(i,b3ip))
        write(971,9003)'L',b3seq,i,n,v
        do j=1,n
          write(971,9004)'F',b3seq,i,j,dble(slsw(j,i,b3ip)),
     1     dble(slsic(j,i,b3ip)),dble(slfsd(j,i,b3ip)),
     1     fgfrst(j,i,b3ip)
        enddo
      enddo
 9000 format(a,1x,a,1x,i18,6(1x,i8))
 9001 format(a,1x,a,1x,i18,7(1x,i8))
 9002 format(a,1x,i18,4(1x,es24.16e3))
 9003 format(a,1x,i18,2(1x,i8),10(1x,es24.16e3))
 9004 format(a,1x,i18,2(1x,i8),3(1x,es24.16e3),1x,i8)
      end

      subroutine b3before(site,field,layer,fine,n,old,
     1 a,b,c,d,e,f,g)
      implicit none
      include 'b03_winter_context.inc'
      integer site,field,layer,fine,n
      double precision old,a,b,c,d,e,f,g
      if(b3on.eq.0.or.b3sel.eq.0)return
      if(b3pending.ne.0)stop 'B03 overlapping assignment'
      b3pending=site
      b3field=field
      b3layer=layer
      b3fine=fine
      b3seq=b3seq+1
      write(971,9000)'B',b3seq,site,field,layer,fine,n,
     1 old,a,b,c,d,e,f,g
 9000 format(a,1x,i18,5(1x,i8),8(1x,es24.16e3))
      end

      subroutine b3after(site,field,layer,fine,value)
      implicit none
      include 'b03_winter_context.inc'
      integer site,field,layer,fine
      double precision value
      if(b3on.eq.0.or.b3sel.eq.0)return
      if(b3pending.ne.site.or.b3field.ne.field.or.
     1 b3layer.ne.layer.or.b3fine.ne.fine)
     1 stop 'B03 assignment pairing'
      b3seq=b3seq+1
      write(971,9000)'A',b3seq,site,field,layer,fine,value
      b3pending=0
 9000 format(a,1x,i18,4(1x,i8),1x,es24.16e3)
      end

      subroutine b3term(direction,a,b)
      implicit none
      include 'b03_winter_context.inc'
      integer direction
      double precision a,b
      if(b3on.eq.0.or.b3sel.eq.0)return
      b3seq=b3seq+1
      write(971,9000)'T',b3seq,direction,a,b
 9000 format(a,1x,i18,1x,i8,2(1x,es24.16e3))
      end

      subroutine b3end
      implicit none
      include 'b03_winter_context.inc'
      call b3open
      if(b3on.eq.0)return
      if(b3pending.ne.0)stop 'B03 incomplete writer at end'
      write(971,'(a,1x,i18)')'B3_DETAIL_END',b3seq
      write(972,'(a,1x,i18)')'B3_CENSUS_END',b3cseq
      close(971)
      close(972)
      b3on=0
      end

      subroutine b3wintercount(yr,dy,ip,calls,ks)
      implicit none
      include 'b03_winter_context.inc'
      integer yr,dy,ip,calls,ks
      call b3open
      if(b3on.eq.0)return
      b3cseq=b3cseq+1
      write(972,9000)'D',b3cseq,yr,dy,ip,calls,ks
 9000 format(a,1x,i18,5(1x,i8))
      end
