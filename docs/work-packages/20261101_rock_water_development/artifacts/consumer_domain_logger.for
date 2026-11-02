C     Original bounded research logger; no model-state writes.
      subroutine rdomain(slot,yr,dy,ip,layer,hr,a,b,c,d)
      use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
      implicit none
      integer slot,yr,dy,ip,layer,hr
      double precision a,b,c,d,gap
      integer cy,cd,j,k,l
      integer*8 cnt(8,3,10),bad(8,3,10),icy(8,3,10)
      integer*8 totals(8),nrows,ndays
      double precision lo(4,8,3,10),hi(2,8,3,10)
      logical first,enabled,sealed,invalid
      save first,enabled,sealed,cy,cd,cnt,bad,icy,totals
      save nrows,ndays,lo,hi
      data first/.true./,enabled/.false./,sealed/.false./
      if(first)then
        inquire(file='consumer_observe.on',exist=enabled)
        if(enabled)then
          open(981,file='consumer-domains.txt',status='new')
          write(981,'(a)')'RD_SCHEMA 2'
        endif
        cnt=0
        bad=0
        icy=0
        totals=0
        nrows=0
        ndays=0
        cy=0
        cd=0
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'RD record after close'
      if(slot.eq.0)then
        call emit
        write(981,9002)totals,nrows,ndays
        close(981)
        sealed=.true.
        return
      endif
      if(slot.lt.1.or.slot.gt.8.or.ip.lt.1.or.ip.gt.3.or.
     1 layer.lt.1.or.layer.gt.10.or.hr.lt.0.or.hr.gt.24)
     2 stop 'RD invalid support'
      if(yr.lt.cy.or.(yr.eq.cy.and.dy.lt.cd))
     1 stop 'RD reversed clock'
      if(yr.ne.cy.or.dy.ne.cd)then
        call emit
        cy=yr
        cd=dy
      endif
      invalid=.not.(ieee_is_finite(a).and.ieee_is_finite(b)
     1 .and.ieee_is_finite(c).and.ieee_is_finite(d))
C     Retain nonfinite evidence without floating-point comparisons.
      if(invalid)then
        write(981,9004)yr,dy,slot,ip,layer,hr,sum(totals)+1,
     1    a,b,c,d
        flush(981)
        return
      endif
      if(slot.eq.1)then
        gap=b-a
        invalid=invalid.or.a.le.0.d0.or.a.ge.b
      else if(slot.eq.8)then
        gap=b
        invalid=invalid.or.a.lt.0.d0.or.b.lt.0.d0
      else
        gap=b
        if(slot.ne.5)invalid=invalid.or.b.le.0.d0
      endif
      cnt(slot,ip,layer)=cnt(slot,ip,layer)+1
      totals(slot)=totals(slot)+1
      if(c.gt.0.d0)icy(slot,ip,layer)=icy(slot,ip,layer)+1
      if(cnt(slot,ip,layer).eq.1)then
        lo(:,slot,ip,layer)=(/a,b,gap,c/)
        hi(:,slot,ip,layer)=(/a,b/)
      else
        lo(1,slot,ip,layer)=min(lo(1,slot,ip,layer),a)
        lo(2,slot,ip,layer)=min(lo(2,slot,ip,layer),b)
        lo(3,slot,ip,layer)=min(lo(3,slot,ip,layer),gap)
        lo(4,slot,ip,layer)=max(lo(4,slot,ip,layer),c)
        hi(1,slot,ip,layer)=max(hi(1,slot,ip,layer),a)
        hi(2,slot,ip,layer)=max(hi(2,slot,ip,layer),b)
      endif
      if(invalid)then
        bad(slot,ip,layer)=bad(slot,ip,layer)+1
        if(bad(slot,ip,layer).eq.1)then
          write(981,9003)yr,dy,slot,ip,layer,hr,sum(totals),
     1      a,b,c,d
          flush(981)
        endif
      endif
      return
 9002 format('RD_END',10(1x,i18))
 9004 format('N',6(1x,i8),1x,i18,4(1x,es24.16e3))
 9003 format('B',6(1x,i8),1x,i18,4(1x,es24.16e3))
      contains
      subroutine emit
      if(sum(cnt).eq.0)return
      ndays=ndays+1
      do j=1,8
        do k=1,3
          do l=1,10
            if(cnt(j,k,l).gt.0)then
              write(981,9001)cy,cd,j,k,l,cnt(j,k,l),
     1          bad(j,k,l),icy(j,k,l),lo(1,j,k,l),hi(1,j,k,l),
     2          lo(2,j,k,l),hi(2,j,k,l),lo(3,j,k,l),lo(4,j,k,l)
              nrows=nrows+1
            endif
          enddo
        enddo
      enddo
      cnt=0
      bad=0
      icy=0
 9001 format('S',5(1x,i8),3(1x,i18),6(1x,es24.16e3))
      end subroutine emit
      end
