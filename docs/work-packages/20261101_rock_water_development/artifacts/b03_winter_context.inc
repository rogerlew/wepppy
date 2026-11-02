C     Original observer-only state, initialized by B3OPEN.
      integer b3yr,b3day,b3ip,b3hr,b3on,b3sel,b3count
      integer b3ys(64),b3ds(64),b3pending,b3field,b3layer,b3fine
      integer*8 b3seq,b3cseq
      common /b3ctx/ b3yr,b3day,b3ip,b3hr,b3on,b3sel,b3count,
     1 b3ys,b3ds,b3pending,b3field,b3layer,b3fine,b3seq,b3cseq
      save /b3ctx/
