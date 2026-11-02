"""Strict interval/hour producer-consumer joins for R05 original observations."""
import struct


def f32(x):return struct.unpack('>f',struct.pack('>f',x))[0]


def cumulative(increments,totals):
    if len(increments)!=len(totals) or not increments:raise ValueError('Missing cumulative endpoints')
    total=0.
    for increment,observed in zip(increments,totals):
        total=f32(total+increment)
        if total!=observed:raise ValueError('Increment/cumulative mismatch or double counting')
    return total


class Joins:
    def __init__(self,windows):
        self.windows=windows;self.idat={};self.wb={};self.published={};self.idat_count=0;self.wb_count=0;self.hour_count=0;self.forcing={};self.ready_stores={};self.winter={};self.melt_series={};self.winter_count=0

    def selected(self,clock):return any(clock[0]==w[0] and w[1]<=clock[1]<=w[2] for w in self.windows)

    def consume(self,row):
        clock=(row['year'],row['day']);key=(*clock,row['ofe']);tag=row['tag'];v=row['values'];ix=row['index'];ip=row['ofe']
        if tag=='DAY_CLOSE_STATE' and key in self.ready_stores:raise ValueError('Daily close with unconsumed IDAT stores')
        if not self.selected(clock):return
        if tag=='WINTER_PRE_STATE':
            if key in self.winter:raise ValueError('Nested winter invocation')
            self.winter[key]=dict(hour=0,phase=None,net={},final={},melt_open=False)
        if key in self.winter:
            winter=self.winter[key]
            stages=('WINTER_WEATHER','WINTER_PARTITION','WINTER_HOUR_FLAGS','WINTER_SNOW_PRE','SNOW_ENTRY','SNOW_RETURN','WINTER_SNOW_POST','WINTER_MELT_HOUR')
            if tag in stages:
                position=stages.index(tag)
                if position==0:
                    if ix!=winter['hour']+1 or winter['phase'] not in (None,len(stages)-1):raise ValueError('Missing/reordered snow hour')
                    winter['hour']=ix;winter['phase']=0;winter['melt_seen']=False
                else:
                    if ix!=winter['hour'] or winter['phase']!=position-1 or winter['melt_open']:raise ValueError('Missing/reordered snow owner endpoint')
                    winter['phase']=position
            if tag=='MELT_RAW':
                if winter['phase']!=4 or winter['melt_open'] or winter['melt_seen']:raise ValueError('Unowned melt calculation')
                winter['melt_open']=True;winter['melt_seen']=True
            if tag=='MELT_RETURN':
                if not winter['melt_open']:raise ValueError('Melt return without raw calculation')
                winter['melt_open']=False
            if tag=='WINTER_NET_HOUR':
                if ix!=len(winter['net'])+1:raise ValueError('Winter corrected-hour order')
                winter['net'][ix]=v
            if tag=='WINTER_FINAL_HOUR':
                if ix!=len(winter['final'])+1 or ix not in winter['net']:raise ValueError('Winter final-hour order')
                before=winter['net'][ix]
                expected=f32(before[0]+before[1]) if before[1]>0 else before[0]
                if v[:3]!=[expected,before[1],before[2]]:raise ValueError('Rain/melt reinsertion ownership mismatch')
                winter['final'][ix]=v
            if tag=='WINTER_RETURN':
                if winter['hour']!=24 or winter['phase']!=len(stages)-1 or winter['melt_open'] or set(winter['final'])!=set(range(1,25)):raise ValueError('Incomplete winter hourly ownership')
                total=cumulative([winter['final'][i][0] for i in range(1,25)],[winter['final'][i][3] for i in range(1,25)])
                if v[1]!=total or v[5]!=total:raise ValueError('Winter daily/hourly melt mismatch')
                self.melt_series[key]={i:winter['final'][i][0] for i in range(1,25)}
                del self.winter[key];self.winter_count+=1
        if tag=='ID_HRMELT' and key in self.melt_series:
            if self.melt_series[key].get(ix)!=v[0]:raise ValueError('Winter/IDAT hourly melt handoff mismatch')
        if tag=='IR_IDAT':
            if key in self.forcing:raise ValueError('Unconsumed IRS forcing call')
            self.forcing[key]=v
        if tag=='ID_ENTRY':
            if key in self.idat:raise ValueError('Nested IDAT invocation')
            forcing=self.forcing.pop(key,None)
            if forcing is None or [v[0],v[1],v[3]]!=[forcing[0],forcing[3],forcing[1]]:raise ValueError('IRS/IDAT primitive forcing mismatch')
            self.idat[key]={'seen':{},'melt_hours':set(),'series':{},'nf':None,'step_pre':{},'step_post':{},'product':{},'result':{},'phase':'setup','next':2,'initial':None,'accepted':None,'returned':None}
        if tag.startswith('ID_'):
            if key not in self.idat:raise ValueError('IDAT record without entry')
            state=self.idat[key]
            state['seen'][tag]=state['seen'].get(tag,0)+1
            if tag=='ID_HRMELT':
                if ix!=len(state['melt_hours'])+1 or ix>24:raise ValueError('Missing/reordered IDAT hourly melt')
                state['melt_hours'].add(ix)
            if tag.startswith('ID_NET_'):state['initial']=(row['kind'],v[0])
            if tag=='ID_ACCEPT':state['accepted']=v
            if tag=='ID_RETURN':state['returned']=v
            if tag=='ID_SIZE':
                if state['nf'] is not None or not 2<=v[0]<=1500:raise ValueError('Invalid/duplicate interval count')
                state['nf']=v[0]
            if tag in ('ID_STORM_PRE','ID_STORM_FINAL','ID_CUM_PRE','ID_CUM_FINAL'):
                group=state['series'].setdefault(tag,{})
                if ix in group:raise ValueError('Duplicate storm endpoint')
                group[ix]=v
            for prefix,name in [('ID_STEP_PRE_','step_pre'),('ID_STEP_POST_','step_post')]:
                if tag.startswith(prefix):
                    if ix in state[name]:raise ValueError('Duplicate depletion step')
                    if name=='step_pre':
                        if ix!=state['next'] or state['phase'] not in ('setup','done'):raise ValueError('Depletion PRE order')
                        state['phase']='pre'
                    else:
                        prior=state['step_pre'].get(ix)
                        expected_phase='product' if prior and prior[1]>0 else 'pre'
                        if ix!=state['next'] or state['phase']!=expected_phase:raise ValueError('Depletion POST order')
                        state['phase']='post'
                    state[name][ix]=(row['kind'],v[0])
            for expected,name in [('ID_PRODUCT','product'),('ID_STORM_POST','result')]:
                if tag==expected:
                    if ix in state[name]:raise ValueError('Duplicate interval arithmetic')
                    if name=='product':
                        if state['phase']!='pre' or ix!=state['next']:raise ValueError('Product order')
                        state['phase']='product'
                    else:
                        if state['phase']!='post' or ix!=state['next']:raise ValueError('Storm result order')
                        state['phase']='done';state['next']+=1
                    state[name][ix]=v
            if tag=='ID_EXIT':
                if key in self.ready_stores:raise ValueError('IDAT publication overwrites unconsumed stores')
                self.finish_idat(state,v[0]);self.ready_stores[key]=state['returned'][:3];del self.idat[key];self.idat_count+=1
        if tag=='WB_ENTRY_WATER' and key in self.ready_stores:
            if v[:3]!=self.ready_stores.pop(key):raise ValueError('IDAT/consumer interception-store join mismatch')
        if tag=='WB_ENTRY_STATE':
            if key in self.wb:raise ValueError('Nested water consumer')
            self.wb[key]=dict(n=None,requests={},closes={},open=set(),closed=set(),transfer_pre={},transfer_post={},up_pre=None,up_post=None)
        if key not in self.wb:
            if tag.startswith(('WB_HOUR_','WB_TRANSFER_')):raise ValueError('Unowned hourly record')
            return
        state=self.wb[key]
        if tag=='WB_HOUR_COUNT':
            if state['n'] is not None or not 1<=v[0]<=24:raise ValueError('Hourly count invalid')
            state['n']=v[0]
        if tag=='WB_HOUR_REQUEST':
            if state['n'] is None or ix!=len(state['requests'])+1 or (ix>1 and ix-1 not in state['closed']):raise ValueError('Missing/reordered hourly request')
            if ip>1:
                upstream=self.published.get((*clock,ip-1))
                if upstream is None or ix not in upstream['transfer_post']:raise ValueError('Missing upstream transfer owner')
                previous=upstream['transfer_post'][ix]
                if v[5:7]!=[previous[0],previous[2]] or v[3]!=upstream['up_post'][0]:raise ValueError('Stale/mismatched upstream hourly forcing')
            if v[0]!=v[1]:raise ValueError('Requested hour/FIN operand mismatch')
            state['requests'][ix]=v
        if tag=='HOUR_OPEN_STATE':
            hour=len(state['requests'])
            if hour==0 or hour in state['open']:raise ValueError('Missing/duplicate hourly opening')
            state['open'].add(hour)
        if tag=='WB_HOUR_CLOSE':
            if ix not in state['open'] or ix in state['closes'] or ix!=len(state['requests']):raise ValueError('Missing/reordered hourly close')
            state['closes'][ix]=v
        if tag=='HOUR_CLOSE_STATE':
            hour=len(state['requests'])
            if hour not in state['closes'] or hour in state['closed']:raise ValueError('Unmatched hour closing state')
            state['closed'].add(hour)
        if tag=='WB_UP_PRE':
            if state['up_pre'] is not None:raise ValueError('Duplicate upstream scalar snapshot')
            state['up_pre']=v
            if any(request[3:5]!=v for request in state['requests'].values()):raise ValueError('Hourly/scalar forcing continuity mismatch')
        if tag=='WB_UP_POST':
            if state['up_pre'] is None or state['up_post'] is not None or v!=[state['up_pre'][1],state['up_pre'][1]]:raise ValueError('Upstream scalar overwrite order/arithmetic mismatch')
            state['up_post']=v
        if tag in ('WB_TRANSFER_PRE','WB_TRANSFER_POST'):
            name='transfer_pre' if tag.endswith('PRE') else 'transfer_post'
            if ix in state[name]:raise ValueError('Duplicate transfer')
            if tag.endswith('POST'):
                before=state['transfer_pre'].get(ix)
                if before is None or v!=[before[1],before[1],before[3],before[3]]:raise ValueError('Transfer copy arithmetic/order mismatch')
                outgoing=state['closes'].get(ix)
                if outgoing is None or [before[1],before[3]]!=outgoing[:2]:raise ValueError('Hourly result/transfer ownership mismatch')
            state[name][ix]=v
        if tag=='WB_RETURN_STATE':
            n=state['n'];expected=set(range(1,(n or 0)+1))
            if not n or any(set(state[name])!=expected for name in ('requests','closes','open','closed','transfer_pre','transfer_post')) or state['up_post'] is None:
                raise ValueError('Incomplete hourly or transfer census')
            rows=[state['closes'][i] for i in range(1,n+1)]
            cumulative([x[0] for x in rows],[x[2] for x in rows])
            cumulative([x[3] for x in rows],[x[4] for x in rows])
            cumulative([x[8] for x in rows],[x[5] for x in rows])
            self.hour_count+=n;self.wb_count+=1;self.published[key]=state;del self.wb[key]

    @staticmethod
    def finish_idat(state,exit_nf):
        if 'seen' in state:
            if state['melt_hours']!=set(range(1,25)):raise ValueError('Incomplete IDAT hourly melt census')
            required=('ID_ENTRY','ID_MODE','ID_CONSTRUCT','ID_CAPACITY','ID_ACCEPT','ID_SIZE','ID_RETURN','ID_EXIT')
            if any(state['seen'].get(tag,0)!=1 for tag in required):raise ValueError('Missing/duplicate IDAT branch owner')
            if sum(n for tag,n in state['seen'].items() if tag.startswith('ID_NET_'))!=1:raise ValueError('Missing/duplicate net-interception owner')
        nf=state['nf']
        if nf is None or nf!=exit_nf:raise ValueError('IDAT exit/count mismatch')
        allpoints=set(range(1,nf+1));steps=set(range(2,nf+1))
        for tag,expected in [('ID_STORM_PRE',allpoints),('ID_STORM_FINAL',allpoints),('ID_CUM_PRE',steps),('ID_CUM_FINAL',steps)]:
            if set(state['series'].get(tag,{}))!=expected:raise ValueError('Missing storm endpoint/cumulative coordinate')
        if any(set(state[name])!=steps for name in ('step_pre','step_post','result')):raise ValueError('Missing depletion endpoint')
        pre=state['series']['ID_STORM_PRE'];post=state['series']['ID_STORM_FINAL'];xy=0.;rawxy=0.
        if state['next']!=nf+1:raise ValueError('Missing final depletion step')
        if state['initial']!=state['step_pre'][2]:raise ValueError('Net interception/depletion join mismatch')
        if state['accepted'] is None or state['returned'] is None or state['accepted'][1:]!=state['returned'][:3]:raise ValueError('Allocated/returned interception stores differ')
        for j in range(2,nf+1):
            kind,net=state['step_pre'][j];outkind,outnet=state['step_post'][j]
            if kind!=outkind:raise ValueError('Depletion kind changes inside call')
            if j>2 and net!=state['step_post'][j-1][1]:raise ValueError('Depletion remainder continuity')
            width=f32(pre[j][0]-pre[j-1][0]);rate=pre[j-1][1]
            if width<0:raise ValueError('Reversed storm support')
            rawxy=f32(rawxy+f32(rate*width))
            if state['series']['ID_CUM_PRE'][j]!=[rawxy]:raise ValueError('Constructed storm cumulative mismatch')
            if net>0:
                product=state['product'].get(j);temp=f32(rate*width)
                if product!=[width,temp,rate,pre[j][0],pre[j-1][0]]:raise ValueError('Storm-product operand join')
                if temp>=net:expected_net=0.;expected_rate=f32(f32(temp-net)/width)
                else:expected_net=f32(net-temp) if kind=='r' else net-temp;expected_rate=0.
            else:
                if j in state['product']:raise ValueError('Product executed on skipped depletion branch')
                expected_net=net;expected_rate=rate
            xy=f32(xy+f32(expected_rate*width))
            if outnet!=expected_net or state['result'][j]!=[expected_rate,xy,xy]:raise ValueError('Native depletion arithmetic mismatch')
            if post[j-1]!=[pre[j-1][0],expected_rate] or state['series']['ID_CUM_FINAL'][j]!=[xy]:raise ValueError('Final storm producer/consumer mismatch')
        if state['returned'][3]!=xy:raise ValueError('Returned storm integral mismatch')
        if post[nf]!=pre[nf]:raise ValueError('Last storm endpoint changed without producer')

    def finish(self):
        if self.idat or self.wb or self.forcing or self.winter or self.ready_stores:raise ValueError('Unclosed interval/hour ownership')
        return dict(idat_invocations=self.idat_count,water_invocations=self.wb_count,hours=self.hour_count,winter_invocations=self.winter_count,passed=True)
