C     Original full-period snow evidence bridge for B04 interaction.
      subroutine b5open
      implicit none
      integer b5seq,b5entries,b5returns,b5on,ios
      common /b5obs/ b5seq,b5entries,b5returns,b5on
      save /b5obs/
      logical first,exists
      save first
      data first/.true./
      if(.not.first)return
      first=.false.
      b5on=0
      b5seq=0
      b5entries=0
      b5returns=0
      inquire(file='combined_snow.on',exist=exists)
      if(.not.exists)return
      open(957,file='combined-snow.txt',status='new',
     1 action='write',iostat=ios)
      if(ios.ne.0)stop 'Combined snow destination'
      write(957,'(a)')'B5 1'
      b5on=1
      end

      subroutine b5r(tag,ofe,hour,n,values,unused)
      implicit none
      character*(*) tag
      integer ofe,hour,n,unused,i,ibits(16)
      real values(n)
      if(n.lt.1.or.n.gt.16)stop 'Combined snow real shape'
      do i=1,n
        ibits(i)=transfer(values(i),ibits(i))
      enddo
      call b5write(tag,ofe,hour,n,ibits,'R')
      end

      subroutine b5i(tag,ofe,hour,n,values,unused)
      implicit none
      character*(*) tag
      integer ofe,hour,n,unused,values(n)
      if(n.lt.1.or.n.gt.16)stop 'Combined snow int shape'
      call b5write(tag,ofe,hour,n,values,'I')
      end

      subroutine b5write(tag,ofe,hour,n,values,kind)
      implicit none
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'cupdate.inc'
      character*(*) tag,kind
      integer ofe,hour,n,values(n),i
      integer b5seq,b5entries,b5returns,b5on
      common /b5obs/ b5seq,b5entries,b5returns,b5on
      save /b5obs/
      call b5open
      if(b5on.eq.0)return
      b5seq=b5seq+1
      if(tag.eq.'SNOW_ENTRY')b5entries=b5entries+1
      if(tag.eq.'SNOW_RETURN')b5returns=b5returns+1
      write(957,100)b5seq,year,sdate,ofe,hour,kind,tag,n,
     1 (values(i),i=1,n)
  100 format(i12,4(1x,i8),1x,a,1x,a,1x,i3,16(1x,i12))
      end

      subroutine b5end
      implicit none
      integer b5seq,b5entries,b5returns,b5on
      common /b5obs/ b5seq,b5entries,b5returns,b5on
      save /b5obs/
      call b5open
      if(b5on.eq.0)return
      write(957,'(a,3(1x,i12))')'END',b5seq,b5entries,b5returns
      close(957)
      b5on=0
      end
