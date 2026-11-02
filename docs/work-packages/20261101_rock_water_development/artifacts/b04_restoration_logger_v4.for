C     Original full-period proposal and bounded restoration observer.
      subroutine b4open
      implicit none
      include 'b04_restoration_context.inc'
      logical first,exists
      integer ios
      save first
      data first/.true./
      if(.not.first)return
      first=.false.
      b4on=0
      inquire(file='b04_restoration.on',exist=exists)
      if(.not.exists)return
      b4seq=0
      b4lseq=0
      b4phaseid=0
      b4frost=0
      b4frzng=0
      b4phaseopen=0
      b4status=0
      b4active=0
      b4segments=0
      b4closed=0
      b4restores=0
      b4funded=0
      b4under=0
      b4pending=0
      open(961,file='b04-restoration-events.txt',status='new',
     1 action='write',iostat=ios)
      if(ios.ne.0)stop 'B04 event destination'
      open(962,file='b04-restoration-lineage.txt',status='new',
     1 action='write',iostat=ios)
      if(ios.ne.0)stop 'B04 lineage destination'
      write(961,'(a)')'B4_EVENTS_SCHEMA 1'
      write(962,'(a)')'B4_LINEAGE_SCHEMA 1'
      b4on=1
      end

      subroutine b4clock(yr,dy,ip,hr)
      implicit none
      include 'b04_restoration_context.inc'
      integer yr,dy,ip,hr
      call b4open
      if(b4on.eq.0)return
      if(b4phaseopen.ne.0.or.b4pending.ne.0)
     1 stop 'B04 incomplete phase at call boundary'
      b4yr=yr
      b4day=dy
      b4ip=ip
      b4hr=hr
      b4dispatch=0
      b4frost=b4frost+1
      end

      subroutine b4phase(layer,cell,qw,b4ftime,er,vt,inc,fe,
     1 qwheat,heat,time)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'b04_restoration_context.inc'
      integer layer,cell
      double precision qw,b4ftime,er,vt,inc,fe,qwheat,heat,time
      if(b4on.eq.0)return
      if(b4phaseopen.ne.0)stop 'B04 overlapping phase'
      b4phaseopen=1
      b4phaseid=b4phaseid+1
      b4status=0
      b4layer=layer
      b4cell=cell
      b4seq=b4seq+1
      write(961,9000)'P',b4seq,b4phaseid,b4yr,b4day,b4ip,
     1 b4hr,b4frost,b4frzng,b4dispatch,layer,cell,nfine(layer),
     1 fgfrst(cell,layer,b4ip),dble(slsw(cell,layer,b4ip)),
     1 dble(slsic(cell,layer,b4ip)),dble(thetdr(layer,b4ip)),
     1 dble(dg(layer,b4ip)),dble(slfsd(cell,layer,b4ip)),
     1 qw,b4ftime,er,vt,inc,fe,qwheat,heat,time
      call b4mark(0)
 9000 format(a,13(1x,i18),14(1x,es24.16e3))
      end

      subroutine b4restore(stage,layer,cell,ice,depth,temp,vfd)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'b04_restoration_context.inc'
      integer stage,layer,cell
      double precision ice,depth,temp,vfd
      if(b4on.eq.0)return
      if(b4phaseopen.ne.1.or.layer.ne.b4layer.or.
     1 cell.ne.b4cell)stop 'B04 restoration phase identity'
      if(stage.eq.0)then
        if(b4status.ne.0)stop 'B04 duplicate restoration'
        b4restores=b4restores+1
        b4status=1
        if(ice.lt.0.d0)b4status=2
        if(b4status.eq.1)then
          b4funded=b4funded+1
        else
          b4under=b4under+1
          if(b4active.eq.0)then
            b4segments=b4segments+1
            b4active=b4segments
          endif
          b4lseq=b4lseq+1
          write(962,9001)'X',b4lseq,b4active,b4phaseid
          call b4snap('TRIGGER',2,b4status)
        endif
      else if(stage.ne.1.or.b4status.eq.0)then
        stop 'B04 restoration stage'
      endif
      b4seq=b4seq+1
      write(961,9000)'R',b4seq,b4phaseid,stage,b4status,
     1 b4active,ice,depth,dble(slsw(cell,layer,b4ip)),
     1 dble(slsic(cell,layer,b4ip)),dble(thetdr(layer,b4ip)),
     1 temp,vfd
      call b4mark(stage+1)
 9000 format(a,5(1x,i18),7(1x,es24.16e3))
 9001 format(a,3(1x,i18))
      end

      subroutine b4phaseend(layer,cell)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'b04_restoration_context.inc'
      integer layer,cell
      if(b4on.eq.0)return
      if(b4phaseopen.ne.1.or.layer.ne.b4layer.or.
     1 cell.ne.b4cell)stop 'B04 phase end identity'
      b4seq=b4seq+1
      write(961,9000)'E',b4seq,b4phaseid,
     1 fgfrst(cell,layer,b4ip),dble(slsw(cell,layer,b4ip)),
     1 dble(slsic(cell,layer,b4ip)),dble(slfsd(cell,layer,b4ip))
      call b4mark(3)
      b4phaseopen=0
 9000 format(a,3(1x,i18),3(1x,es24.16e3))
      end

      subroutine b4end
      implicit none
      include 'b04_restoration_context.inc'
      call b4open
      if(b4on.eq.0)return
      if(b4phaseopen.ne.0.or.b4pending.ne.0.or.b4active.ne.0)
     1 stop 'B04 unresolved lineage or phase at end'
      write(961,9000)'END',b4seq,b4phaseid,b4restores,
     1 b4funded,b4under,b4segments,b4closed
      write(962,'(a,1x,i18)')'B4_LINEAGE_END',b4lseq
      close(961)
      close(962)
      b4on=0
 9000 format(a,7(1x,i18))
      end

      subroutine b4snap(tag,mode,code)
      implicit none
      include 'pmxnsl.inc'
      include 'pmxhil.inc'
      include 'pmxpln.inc'
      include 'cwater.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'csaxp.inc'
      include 'b04_restoration_context.inc'
      character*(*) tag
      integer mode,code,i,j,n
      double precision v(10)
      if(b4on.eq.0)return
      if(tag.eq.'FRZNG_PRE')b4frzng=b4frzng+1
      if(tag.eq.'DISPATCH')b4dispatch=code
      b4seq=b4seq+1
      write(961,9010)'C',b4seq,b4frost,b4frzng,b4yr,b4day,
     1 b4ip,b4hr,code,mode,tag
      if(b4active.eq.0)return
      if(b4pending.ne.0)stop 'B03 snapshot inside assignment'
      b4lseq=b4lseq+1
      if(nsl(b4ip).lt.1.or.nsl(b4ip).gt.mxnsl)
     1 stop 'B03 coarse bounds'
      write(962,9001)'H',tag,b4lseq,b4yr,b4day,b4ip,b4hr,
     1 code,mode,nsl(b4ip)
      if(mode.eq.0)return
      write(962,9002)'G',b4lseq,dble(frdp(b4ip)),
     1 dble(thdp(b4ip)),dble(watpdg(b4ip)),dble(watbtm(b4ip))
      do i=1,nsl(b4ip)
        n=0
        if(mode.eq.2)then
          n=nfine(i)
          if(n.lt.1.or.n.gt.10)stop 'B03 fine bounds'
        endif
        v(1)=dble(st(i,b4ip))
        v(2)=dble(frzw(i,b4ip))
        v(3)=dble(dg(i,b4ip))
        v(4)=dble(frozen(i,b4ip))
        v(5)=dble(thetdr(i,b4ip))
        v(6)=dble(ul(i,b4ip))
        v(7)=dble(soilw(i,b4ip))
        v(8)=dble(yst(i,b4ip))
        v(9)=dble(nwfrzz(i,b4ip))
        v(10)=dble(saxfc(i,b4ip))
        write(962,9003)'L',b4lseq,i,n,v
        do j=1,n
          write(962,9004)'F',b4lseq,i,j,dble(slsw(j,i,b4ip)),
     1     dble(slsic(j,i,b4ip)),dble(slfsd(j,i,b4ip)),
     1     fgfrst(j,i,b4ip)
        enddo
      enddo
      if(tag.eq.'FW0_POST')then
        if(b4pending.ne.0)stop 'B04 unresolved writer at FW0'
        b4lseq=b4lseq+1
        write(962,9011)'Z',b4lseq,b4active,b4frost,b4frzng
        b4active=0
        b4closed=b4closed+1
      endif
 9010 format(a,9(1x,i18),1x,a)
 9011 format(a,4(1x,i18))
 9000 format(a,1x,a,1x,i18,6(1x,i8))
 9001 format(a,1x,a,1x,i18,7(1x,i8))
 9002 format(a,1x,i18,4(1x,es24.16e3))
 9003 format(a,1x,i18,2(1x,i8),10(1x,es24.16e3))
 9004 format(a,1x,i18,2(1x,i8),3(1x,es24.16e3),1x,i8)
      end

      subroutine b4before(site,field,layer,fine,n,old,
     1 a,b,c,d,e,f,g)
      implicit none
      include 'b04_restoration_context.inc'
      integer site,field,layer,fine,n
      double precision old,a,b,c,d,e,f,g
      if(b4on.eq.0.or.b4active.eq.0)return
      if(b4pending.ne.0)stop 'B03 overlapping assignment'
      b4pending=site
      b4field=field
      b4wlayer=layer
      b4wcell=fine
      b4lseq=b4lseq+1
      write(962,9000)'B',b4lseq,site,field,layer,fine,n,
     1 old,a,b,c,d,e,f,g
 9000 format(a,1x,i18,5(1x,i8),8(1x,es24.16e3))
      end

      subroutine b4after(site,field,layer,fine,value)
      implicit none
      include 'b04_restoration_context.inc'
      integer site,field,layer,fine
      double precision value
      if(b4on.eq.0.or.b4active.eq.0)return
      if(b4pending.ne.site.or.b4field.ne.field.or.
     1 b4wlayer.ne.layer.or.b4wcell.ne.fine)
     1 stop 'B03 assignment pairing'
      b4lseq=b4lseq+1
      write(962,9000)'A',b4lseq,site,field,layer,fine,value
      b4pending=0
 9000 format(a,1x,i18,4(1x,i8),1x,es24.16e3)
      end

      subroutine b4term(direction,a,b)
      implicit none
      include 'b04_restoration_context.inc'
      integer direction
      double precision a,b
      if(b4on.eq.0.or.b4active.eq.0)return
      b4lseq=b4lseq+1
      write(962,9000)'T',b4lseq,direction,a,b
 9000 format(a,1x,i18,1x,i8,2(1x,es24.16e3))
      end


      subroutine b4mark(stage)
      implicit none
      include 'b04_restoration_context.inc'
      integer stage
      if(b4on.eq.0.or.b4active.eq.0)return
      b4lseq=b4lseq+1
      write(962,9000)'Y',b4lseq,b4phaseid,stage
 9000 format(a,3(1x,i18))
      end
