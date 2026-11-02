C     P03 full-history hourly domain census, adapted from B02.
      subroutine p3dom(slot,yr,dy,ip,layer,hr,a,b,c,d)
      use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
      implicit none
      integer slot,yr,dy,ip,layer,hr,cy,cd,j,k,l,eh
      integer clock_ip,clock_hr,clock_year,clock_day
      integer*8 cnt(14,3,10),bad(14,3,10),icy(14,3,10)
      integer*8 selected(14,3,10),totals(14),nrows,ndays
      double precision a,b,c,d,gap,lo(4,14,3,10),hi(2,14,3,10)
      logical first,enabled,sealed,invalid,pick
      save first,enabled,sealed,cy,cd,cnt,bad,icy,totals,selected
      save nrows,ndays,lo,hi,clock_ip,clock_hr,clock_year,clock_day
      data first/.true./,enabled/.false./,sealed/.false./
      if(first)then
        inquire(file='p03_domain.on',exist=enabled)
        if(enabled)then
          open(972,file='p03-domains.txt',status='new')
          write(972,'(a)')'P3_DOMAIN_SCHEMA 1'
        endif
        cnt=0
        bad=0
        icy=0
        selected=0
        totals=0
        nrows=0
        ndays=0
        cy=0
        cd=0
        clock_ip=0
        clock_hr=0
        clock_year=0
        clock_day=0
        first=.false.
      endif
      if(.not.enabled)return
      if(sealed)stop 'P03 domain record after close'
      if(slot.eq.0)then
        call emit
        write(972,9002)totals,nrows,ndays
        close(972)
        sealed=.true.
        return
      endif
      if(slot.lt.1.or.slot.gt.14.or.ip.lt.1.or.ip.gt.3.or.
     1 layer.lt.1.or.layer.gt.10.or.hr.lt.0.or.hr.gt.24)
     2 stop 'P03 domain invalid support'
      if(yr.lt.cy.or.(yr.eq.cy.and.dy.lt.cd))
     1 stop 'P03 domain reversed clock'
      if(yr.ne.cy.or.dy.ne.cd)then
        call emit
        cy=yr
        cd=dy
      endif
      eh=hr
      if(slot.eq.12)then
        clock_ip=ip
        clock_hr=hr
        clock_year=yr
        clock_day=dy
      endif
      if(slot.ne.1.and.slot.ne.5)then
        if(yr.ne.clock_year.or.dy.ne.clock_day.or.
     1      ip.ne.clock_ip)stop 'P03 domain missing hourly context'
        if(eh.eq.0)eh=clock_hr
        if(eh.lt.1.or.eh.gt.24)stop 'P03 domain missing hour'
      endif
      invalid=.not.(ieee_is_finite(a).and.ieee_is_finite(b)
     1 .and.ieee_is_finite(c).and.ieee_is_finite(d))
      if(invalid)then
        write(972,9004)yr,dy,slot,ip,layer,eh,sum(totals)+1,
     1    a,b,c,d
        flush(972)
        return
      endif
      gap=b
      if(slot.eq.1)then
        gap=b-a
        invalid=a.le.0.d0.or.a.ge.b
      else if(slot.eq.8)then
        invalid=a.lt.0.d0.or.b.le.0.d0
      else if(slot.eq.13)then
        invalid=.false.
      else if(slot.ne.5.and.slot.ne.9.and.slot.ne.10)then
        invalid=b.le.0.d0
      endif
      pick=.false.
      if(slot.eq.9)pick=a.gt.0.d0
      if(slot.eq.13)pick=a.ge.b.and.d.eq.1.d0
      if(slot.eq.14)pick=a.lt.dble(0.95)
      cnt(slot,ip,layer)=cnt(slot,ip,layer)+1
      totals(slot)=totals(slot)+1
      if(c.gt.0.d0)icy(slot,ip,layer)=icy(slot,ip,layer)+1
      if(pick)selected(slot,ip,layer)=selected(slot,ip,layer)+1
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
          write(972,9003)yr,dy,slot,ip,layer,eh,sum(totals),
     1      a,b,c,d
          flush(972)
        endif
      endif
      return
 9002 format('P3_DOMAIN_END',16(1x,i18))
 9004 format('N',6(1x,i8),1x,i18,4(1x,es24.16e3))
 9003 format('B',6(1x,i8),1x,i18,4(1x,es24.16e3))
      contains
      subroutine emit
      if(sum(cnt).eq.0)return
      ndays=ndays+1
      do j=1,14
        do k=1,3
          do l=1,10
            if(cnt(j,k,l).gt.0)then
              write(972,9001)cy,cd,j,k,l,cnt(j,k,l),
     1          bad(j,k,l),icy(j,k,l),selected(j,k,l),
     2          lo(1,j,k,l),hi(1,j,k,l),lo(2,j,k,l),
     3          hi(2,j,k,l),lo(3,j,k,l),lo(4,j,k,l)
              nrows=nrows+1
            endif
          enddo
        enddo
      enddo
      cnt=0
      bad=0
      icy=0
      selected=0
 9001 format('S',5(1x,i8),4(1x,i18),6(1x,es24.16e3))
      end subroutine emit
      end
