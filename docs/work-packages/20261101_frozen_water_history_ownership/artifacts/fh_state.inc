c     Authored observer-only state; never part of a native model COMMON.
      integer fh_seq,fh_maps,fh_hour,fh_mode,fh_current,
     1 fh_seen(mxnsl,mxplan),fh_last(mxplan),fh_kind(mxplan),
     1 fh_parent(mxplan),fh_epoch(mxplan)
      logical fh_enabled,fh_readyv(mxplan),fh_phase(mxplan),
     1 fh_initial(mxplan),fh_popen(mxplan),fh_iopen(mxplan)
      common /fhbook/ fh_seq,fh_maps,fh_hour,fh_mode,fh_current,
     1 fh_seen,fh_last,fh_kind,fh_parent,fh_epoch,fh_enabled,
     1 fh_readyv,fh_phase,
     1 fh_initial,fh_popen,fh_iopen
