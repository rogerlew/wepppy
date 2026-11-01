c     Authored observational helper. All native COMMONs are read-only.
      subroutine fh_setup
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      logical first
      integer ios
      save first
      data first/.true./
      if(.not.first)return
      first=.false.
      fh_seq=0
      fh_maps=0
      fh_hour=0
      fh_mode=-1
      fh_current=0
      fh_seen=0
      fh_last=0
      fh_kind=0
      fh_parent=0
      fh_epoch=0
      fh_readyv=.false.
      fh_phase=.false.
      fh_initial=.false.
      fh_popen=.false.
      fh_iopen=.false.
      inquire(file='frwatc_history.on',exist=fh_enabled)
      if(fh_enabled)then
        open(971,file='frwatc-history.txt',status='new',
     1   action='write',iostat=ios)
        if(ios.ne.0)stop 'FH cannot create fresh observation'
        write(971,'(a)') 'FH_SCHEMA 1'
      endif
      return
      end

      subroutine fh_head(tag,hour,mode)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      character*(*) tag
      integer hour,mode
      call fh_setup
      if(.not.fh_enabled)return
      if(iplane.lt.1.or.iplane.gt.mxplan)stop 'FH bad OFE'
      fh_seq=fh_seq+1
      fh_hour=hour
      fh_mode=mode
      write(971,9000)tag,fh_seq,fh_current,year,sdate,iplane,
     1 hour,mode,nsl(iplane),fh_parent(iplane),fh_epoch(iplane)
 9000 format('E ',a,10(1x,i12))
      return
      end

      subroutine fh_mark(tag,hour,value)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      character*(*) tag
      integer hour,value
      call fh_setup
      if(.not.fh_enabled)return
      fh_current=0
      call fh_head(tag,hour,-1)
      write(971,'(a,2(1x,i12))') 'V',fh_seq,value
      if(tag.eq.'FROST_CALL')fh_parent(iplane)=fh_seq
      if(tag.eq.'FROST_DONE')fh_parent(iplane)=0
      return
      end

      subroutine fh_dump(tag,hour,mode,full)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      character*(*) tag
      integer hour,mode,full,i,j,n,available
      real uf,fh_fc_obs
      call fh_setup
      if(.not.fh_enabled)return
      call fh_head(tag,hour,mode)
      if(nsl(iplane).lt.0.or.nsl(iplane).gt.mxnsl)
     1 stop 'FH bad coarse support'
      do i=1,nsl(iplane)
        n=0
        available=0
        fh_fc_obs=0.0
        if(full.eq.1.and.fh_readyv(iplane))then
          if(nfine(i).ge.1.and.nfine(i).le.10)then
            if(nfine(i).eq.fh_seen(i,iplane))then
              n=nfine(i)
              available=1
              fh_fc_obs=saxfc(i,iplane)
            endif
          endif
        endif
        write(971,9000)fh_seq,i,n,available,dg(i,iplane),
     1   thetdr(i,iplane),ul(i,iplane),st(i,iplane),
     1   frzw(i,iplane),frozen(i,iplane),soilw(i,iplane),
     1   yst(i,iplane),nwfrzz(i,iplane),fh_fc_obs
        do j=1,n
          uf=dg(i,iplane)/n-slfsd(j,i,iplane)
          write(971,9010)fh_seq,i,j,slfsd(j,i,iplane),
     1     slsw(j,i,iplane),slsic(j,i,iplane),uf
        enddo
      enddo
 9000 format('C',4(1x,i12),10(1x,es24.16e3))
 9010 format('F',3(1x,i12),4(1x,es24.16e3))
      return
      end

      subroutine fh_map(stage,mode,hour)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      integer stage,mode,hour
      call fh_setup
      if(.not.fh_enabled)return
      if(stage.eq.0)then
        fh_maps=fh_maps+1
        fh_current=fh_maps
        fh_last(iplane)=fh_current
        call fh_dump('MAP_PRE',hour,mode,1)
      else
        fh_current=fh_last(iplane)
        call fh_dump('MAP_POST',hour,mode,1)
        fh_phase(iplane)=.true.
        if(mode.eq.0)fh_initial(iplane)=.true.
      endif
      return
      end

      subroutine fh_branch(tag,i,j,a,b,c,d,e,f)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      character*(*) tag
      integer i,j
      logical available
      real a,b,c,d,e,f
      call fh_setup
      if(.not.fh_enabled)return
      call fh_head(tag,fh_hour,fh_mode)
c     Do not dereference fine-value arguments without provenance.
      available=fh_readyv(iplane)
      if(i.lt.0.or.i.gt.nsl(iplane))available=.false.
      if(i.ge.1.and.i.le.nsl(iplane))then
        available=available.and.nfine(i).eq.fh_seen(i,iplane)
      endif
      if(.not.available)then
        write(971,'(a,3(1x,i12))')'G',fh_seq,i,j
        return
      endif
      write(971,9000)fh_seq,i,j,a,b,c,d,e,f
 9000 format('B',3(1x,i12),6(1x,es24.16e3))
      return
      end

      subroutine fh_init(kind,hour)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      integer kind,hour
      call fh_setup
      if(.not.fh_enabled)return
      fh_kind(iplane)=kind
      fh_epoch(iplane)=fh_epoch(iplane)+1
      fh_iopen(iplane)=fh_initial(iplane).or.fh_phase(iplane)
      call fh_mark('FN_INIT',hour,kind)
      if(fh_iopen(iplane))then
        fh_current=fh_last(iplane)
        call fh_dump('INIT_PRE',hour,-1,1)
      endif
      return
      end

      subroutine fh_ready(hour)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      integer hour,i
      logical valid
      call fh_setup
      if(.not.fh_enabled)return
      if(nsl(iplane).lt.1.or.nsl(iplane).gt.mxnsl)then
        fh_readyv(iplane)=.false.
        call fh_mark('FN_READY',hour,0)
        return
      endif
      valid=.true.
      do i=1,nsl(iplane)
        valid=valid.and.nfine(i).ge.1.and.nfine(i).le.10
c       Only complete no-frost or synthetic initialization establishes
c       coverage; initial-frost loops can leave earlier cells untouched.
        if(fh_kind(iplane).ne.1.and.fh_kind(iplane).ne.3)then
          valid=valid.and.fh_readyv(iplane)
          valid=valid.and.nfine(i).eq.fh_seen(i,iplane)
        endif
      enddo
      fh_readyv(iplane)=valid
      if(valid)then
        do i=1,nsl(iplane)
          fh_seen(i,iplane)=nfine(i)
        enddo
      endif
      call fh_mark('FN_READY',hour,merge(1,0,valid))
      if(fh_iopen(iplane))then
        fh_current=fh_last(iplane)
        call fh_dump('INIT_POST',hour,-1,1)
        fh_initial(iplane)=.false.
        fh_phase(iplane)=.false.
      endif
      fh_iopen(iplane)=.false.
      fh_kind(iplane)=0
      return
      end

      subroutine fh_follow(stage,hour,phasekind)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      integer stage,hour,phasekind
      call fh_setup
      if(.not.fh_enabled)return
      if(stage.eq.0)then
        fh_popen(iplane)=fh_phase(iplane).and.phasekind.ne.0
        if(fh_popen(iplane))then
          fh_current=fh_last(iplane)
          call fh_dump('FROST_BLOCK_PRE',hour,phasekind,1)
        endif
      elseif(fh_popen(iplane))then
        fh_current=fh_last(iplane)
        call fh_dump('FROST_BLOCK_POST',hour,phasekind,1)
        fh_phase(iplane)=.false.
        fh_popen(iplane)=.false.
      endif
      return
      end

      subroutine fh_coarse(tag,hour)
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      character*(*) tag
      integer hour
      call fh_setup
      if(.not.fh_enabled)return
      fh_current=0
      call fh_dump(tag,hour,-1,0)
      return
      end

      subroutine fh_finish
      include 'pmxtil.inc'
      include 'pmxtls.inc'
      include 'pmxpln.inc'
      include 'pmxhil.inc'
      include 'pmxnsl.inc'
      include 'cstruc.inc'
      include 'cupdate.inc'
      include 'cwint.inc'
      include 'cflgfs.inc'
      include 'cpfrst.inc'
      include 'csaxp.inc'
      include 'cwater.inc'
      include 'fh_state.inc'
      call fh_setup
      if(.not.fh_enabled)return
      write(971,'(a,2(1x,i12))') 'FH_END',fh_seq,fh_maps
      close(971)
      return
      end
