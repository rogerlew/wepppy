"""Source-bound baseline frost exposure selector with explicit temporal support."""
import calendar

def select_events(events,expected_daily=None):
    if expected_daily is None:
        expected_daily={(o,d,y) for o in range(1,4) for y in range(1,17) for d in range(1,367 if calendar.isleap(y) else 366)}
    counts={}; pending={}; completed={}; gates=set(); wbkeys=set(); clocks={}; selected=None; maximum=0.;footer=False
    for e in events:
        tag=e['tag'];counts[tag]=counts.get(tag,0)+1
        if tag=='FOOTER': footer=True;continue
        if footer:raise ValueError('Event after footer')
        ofe=e['ofe'];clock=(e['year'],e['day']);key=(ofe,e['day'],e['year'])
        if ofe not in (1,2,3) or clock<clocks.get(ofe,clock):raise ValueError('OFE/clock drift')
        clocks[ofe]=clock
        if tag=='FROST_CALL':
            if ofe in pending or e['parent']:raise ValueError('Nested/orphan frost call')
            pending[ofe]=(e['seq'],e['year'],e['day'],e['hour'])
        else:
            if e['parent']!=(pending[ofe][0] if ofe in pending else 0):raise ValueError('Frost parent mismatch')
            if tag=='FROST_DONE':
                if ofe not in pending or tuple(e[k] for k in ['year','day','hour'])!=pending[ofe][1:]:raise ValueError('Frost return clock mismatch')
                completed[ofe]=pending.pop(ofe)
        if tag=='DAY_WIN_GATE':
            if key in gates:raise ValueError('Duplicate daily gate')
            gates.add(key)
        if tag=='WB_PRE':
            if key not in gates or key in wbkeys:raise ValueError('WB daily support')
            wbkeys.add(key)
            frozen=sum(x['frozen'] for x in e['layers'].values());maximum=max(maximum,frozen)
            if selected is None and ofe==1 and e['day']>=2 and ofe in completed and frozen>0:
                invalid=[]
                for i,x in e['layers'].items():
                    liquid=x['st']+x['dry']*(x['dg']-x['frozen']);ice=x['frzw']+x['dry']*x['frozen']
                    if x['dg']<=0 or not 0<=x['frozen']<=x['dg'] or liquid<0 or ice<0:invalid.append(i)
                selected=dict(target=[e['year'],e['day']],event_sequence=e['seq'],ofe=ofe,nsl=e['nsl'],last_completed_frost=completed[ofe],frozen_thickness_m=frozen,invalid_coarse_support_layers=invalid,meaning='Exposure selector, not physical-validity admission')
    if not footer or pending or gates!=expected_daily:raise ValueError('Incomplete frost/daily support')
    return dict(counts=counts,selection=selected,selected=None if selected is None else selected['target'],max_coarse_frozen_m=maximum,complete_daily_gates=len(gates))
