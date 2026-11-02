C     Original B02 initialization observer. Never writes model state.
      subroutine b2obs(tag,ip,cell,source,a,b,c,d,e,f)
      implicit none
      character*(*) tag
      integer ip,cell,source,ios
      integer*8 seq
      double precision a,b,c,d,e,f
      logical first,enabled,sealed
      save seq,first,enabled,sealed
      data seq/0/,first/.true./,enabled/.false./
      data sealed/.false./
      if(first)then
        inquire(file='b02_observe.on',exist=enabled)
        if(enabled)then
          open(978,file='b02-initialization.txt',status='new',
     1      action='write',iostat=ios)
          if(ios.ne.0)stop 'B02 trace destination exists'
          write(978,'(a)')'B2_SCHEMA 1'
        endif
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'B02 initialization trace already closed'
      if(tag.eq.'END')then
        write(978,'(a,1x,i18)')'B2_END',seq
        close(978)
        sealed=.true.
        return
      endif
      seq=seq+1
      write(978,9000)tag,seq,ip,cell,source,a,b,c,d,e,f
 9000 format(a,1x,i18,3(1x,i8),6(1x,es24.16e3))
      return
      end
