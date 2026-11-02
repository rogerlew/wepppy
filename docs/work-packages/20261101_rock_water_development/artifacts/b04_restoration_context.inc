C     Original observation-only context; no model state aliases.
      integer b4on,b4seq,b4lseq,b4phaseid,b4frost,b4frzng,
     1 b4yr,b4day,b4ip,b4hr,b4dispatch,b4layer,b4cell,
     1 b4phaseopen,b4status,b4active,b4segments,b4closed,
     1 b4restores,b4funded,b4under,b4pending,b4field,
     1 b4wlayer,b4wcell
      common /b04obs/ b4on,b4seq,b4lseq,b4phaseid,b4frost,
     1 b4frzng,b4yr,b4day,b4ip,b4hr,b4dispatch,b4layer,
     1 b4cell,b4phaseopen,b4status,b4active,b4segments,
     1 b4closed,b4restores,b4funded,b4under,b4pending,
     1 b4field,b4wlayer,b4wcell
      save /b04obs/
