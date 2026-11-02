C     Original P03 initialization observer. Never writes model state.
      subroutine p3ini(tag,ip,cell,source,a,b,c,d,e,f)
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
        inquire(file='p03_init.on',exist=enabled)
        if(enabled)then
          open(978,file='p03-initialization.txt',status='new',
     1      action='write',iostat=ios)
          if(ios.ne.0)stop 'P03 trace destination exists'
          write(978,'(a)')'P3_INIT_SCHEMA 1'
        endif
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'P03 initialization trace already closed'
      if(tag.eq.'END')then
        write(978,'(a,1x,i18)')'P3_INIT_END',seq
        close(978)
        sealed=.true.
        return
      endif
      seq=seq+1
      write(978,9000)tag,seq,ip,cell,source,a,b,c,d,e,f
 9000 format(a,1x,i18,3(1x,i8),6(1x,es24.16e3))
      return
      end
