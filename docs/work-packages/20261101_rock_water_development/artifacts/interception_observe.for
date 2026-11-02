C     Original observer: daily interception producer/consumer operands.
C     No native state writes. Calls retain global update-clock identity.
      subroutine icobs(tag,ip,a,b,c,d,e,f,g,h,q,r,s,t)
      include 'pmxpln.inc'
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'cupdate.inc'
      character*(*) tag
      integer ip
      double precision a,b,c,d,e,f,g,h,q,r,s,t
      logical first,enabled,sealed
      integer*8 records
      save first,enabled,sealed,records
      data first/.true./,enabled/.false./,sealed/.false./
      if(first)then
        inquire(file='interception_observe.on',exist=enabled)
        if(enabled)then
          open(979,file='interception-ownership.txt',status='new')
          write(979,'(a)')'IO_SCHEMA 1'
        endif
        records=0
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'IO record after close'
      if(tag.eq.'END')then
        write(979,'(a,1x,i18)')'IO_END',records
        close(979)
        sealed=.true.
        return
      endif
      records=records+1
      write(979,9000)tag,year,sdate,ip,records,
     1 a,b,c,d,e,f,g,h,q,r,s,t
 9000 format(a,3(1x,i8),1x,i18,12(1x,es24.16e3))
      return
      end
