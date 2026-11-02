"""Mandatory WB and bounded SWU observation ownership; no native execution."""
from r05_flow_joins import f32


class Causal:
    def __init__(self,windows):
        self.windows=windows;self.snapshots={};self.water={};self.swu={};self.water_calls=0;self.swu_calls=0;self.idat={};self.ready_stores={}

    def consume(self,row):
        tag=row['tag'];key=(row['year'],row['day'],row['ofe']);v=row['values'];ix=row['index']
        selected=any(key[0]==y and first<=key[1]<=last for y,first,last in self.windows)
        if tag=='ID_ENTRY':
            if key in self.idat or key in self.ready_stores:raise ValueError('Unconsumed IDAT invocation/publication')
            self.idat[key]=None
        if tag=='ID_RETURN':
            if key not in self.idat or self.idat[key] is not None:raise ValueError('Unowned/repeated IDAT return')
            self.idat[key]=v[:3]
        if tag=='ID_EXIT':
            if key not in self.idat or self.idat[key] is None:raise ValueError('IDAT exit before store return')
            self.ready_stores[key]=self.idat.pop(key)
        if tag=='WB_ENTRY_WATER' and key in self.ready_stores:
            if v[:3]!=self.ready_stores.pop(key):raise ValueError('IDAT/water store ownership mismatch')
        if tag=='DAY_CLOSE_STATE' and (key in self.idat or key in self.ready_stores):raise ValueError('Unconsumed daily IDAT store publication')
        stage=row.get('snapshot');group=row.get('group')
        if stage is not None:
            sk=(*key,stage)
            if group=='LAYER' and ix==1:self.snapshots[sk]={'layers':{}}
            snapshot=self.snapshots[sk]
            if group=='LAYER':snapshot['layers'][ix]=v
            else:snapshot[group]=v
            if group!='STATE':return
            del self.snapshots[sk]
        else:snapshot=None
        if tag=='WB_ENTRY_STATE':
            if key in self.water:raise ValueError('Nested causal water invocation')
            self.water[key]=dict(phase='entry',entry=snapshot,et=False)
        if tag in ('WB_FIN','WB_RESET','WB_ET_STORE','WB_DAILY_FLUX'):
            if key not in self.water:raise ValueError('Causal scalar without water owner')
            state=self.water[key]
            expected={'WB_FIN':'entry','WB_RESET':'fin','WB_ET_STORE':'reset','WB_DAILY_FLUX':'store'}[tag]
            if state['phase']!=expected:raise ValueError('Missing/reordered/duplicate causal water scalar')
            if tag=='WB_FIN':
                before=state['entry']['WATER'];plant=state['entry']['PLANT'];plaint,resint,pintlv=before[:3]
                if plaint<f32(1e-8) and pintlv>f32(1e-8):
                    if plant[3]>0 and plant[0]>0:plaint=pintlv
                    else:resint=f32(resint+pintlv)
                if v[:2]!=before[8:10] or v[4:7]!=[plaint,resint,pintlv]:raise ValueError('WB entry/FIN carry or forcing mismatch')
                state['phase']='fin';state['fin']=v
            elif tag=='WB_RESET':
                if v!=[0.]:raise ValueError('Carry reset mismatch')
                state['phase']='reset'
            elif tag=='WB_ET_STORE':
                if not state['et'] or key in self.swu:raise ValueError('ET store before completed ET/withdrawal')
                endpoint=state.get('pre_withdrawal')
                if endpoint is not None and endpoint['WATER'][3]>0 and endpoint['PLANT'][3]>0 and 'swu_return' not in state:raise ValueError('Missing required withdrawal invocation')
                if 'swu_return' in state:
                    returned=state['swu_return']
                    if v[:6]!=returned[3:6]+returned[:3]:raise ValueError('Withdrawal return/ET store handoff mismatch')
                state['phase']='store';state['store']=v
                expected_partition=f32(v[3]-v[5]) if v[3]>0 and v[5]>0 else v[3] if v[3]>0 else 0.
                if v[6]!=expected_partition:raise ValueError('Canopy ET partition mismatch')
            else:
                stored=state['store']
                if v[9:12]!=stored[:3] or v[17:20]!=[stored[5],stored[4],0.]:raise ValueError('ET store/daily flux handoff mismatch')
                state['phase']='flux'
        if tag in ('EVAP_PRE_STATE','EVAPPM_PRE_STATE','WB_HOUR_COUNT'):
            if key not in self.water or self.water[key]['phase']!='reset':raise ValueError('Consumer before FIN/reset')
        if tag in ('EVAP_POST_STATE','EVAPPM_POST_STATE'):
            if key not in self.water:raise ValueError('ET without water owner')
            self.water[key]['et']=True
        if tag in ('PTGRP_PRE_STATE','PTGRA_PRE_STATE'):
            if key not in self.water or self.water[key]['phase']!='reset':raise ValueError('Growth after ET-store handoff')
        if tag in ('PTGRP_POST_STATE','PTGRA_POST_STATE'):
            self.water[key]['pre_withdrawal']=snapshot
        if tag=='SWU_PRE_STATE':
            if key not in self.water or self.water[key]['phase']!='reset' or not self.water[key]['et'] or key in self.swu:raise ValueError('Unowned/repeated withdrawal')
            ep=snapshot['WATER'][3];plaint=snapshot['WATER'][0]
            demand=f32(ep-plaint) if plaint>0 else ep
            root=min(snapshot['PLANT'][3],snapshot['layers'][len(snapshot['layers'])][7])
            last=next((j for j,layer in snapshot['layers'].items() if root<=layer[7]),len(snapshot['layers']))
            self.swu[key]=dict(pre=snapshot,phase='request',next=1,last=last if demand>0 else 0,demand=max(0.,demand),root=root,xx=0.,stocks={})
        if tag in ('SWU_REQUEST','SWU_ACCEPT','SWU_STOCK'):
            if not selected or key not in self.swu:raise ValueError('Withdrawal layer record without owner/window')
            state=self.swu[key]
            expected={'SWU_REQUEST':'request','SWU_ACCEPT':'accept','SWU_STOCK':'stock'}[tag]
            if state['phase']!=expected or ix!=state['next'] or ix>state['last']:raise ValueError('Withdrawal layer sequence/cardinality mismatch')
            layer=state['pre']['layers'][ix]
            if tag=='SWU_REQUEST':
                gx=layer[7] if ix<state['last'] else state['root']
                if v[1]!=state['xx'] or v[2]!=f32(v[0]-v[1]) or v[3:7]!=[state['demand'],state['root'],gx,layer[0]]:raise ValueError('Withdrawal request operands mismatch')
                state['request']=v;state['phase']='accept'
            elif tag=='SWU_ACCEPT':
                if v[0]!=state['request'][6]:raise ValueError('Withdrawal acceptance stock owner mismatch')
                state['accept']=v;state['phase']='stock'
            else:
                before,uptake=state['accept'];stock=f32(before-uptake)
                if stock<f32(1e-10):stock=0.
                total=f32(state['xx']+uptake)
                if v!=[stock,uptake,total]:raise ValueError('Accepted withdrawal/stock arithmetic mismatch')
                state['stocks'][ix]=stock;state['xx']=total;state['next']+=1;state['phase']='request'
        if tag=='SWU_POST_STATE':
            if key not in self.swu:raise ValueError('Withdrawal return without owner')
            state=self.swu.pop(key)
            if selected:
                if state['phase']!='request' or state['next']!=state['last']+1:raise ValueError('Incomplete withdrawal layer endpoints')
                for j,layer in snapshot['layers'].items():
                    if layer[0]!=state['stocks'].get(j,state['pre']['layers'][j][0]):raise ValueError('Withdrawal layer/post-state mismatch')
                pre=state['pre']['WATER'];post=snapshot['WATER'];expected=f32(state['xx']+pre[0]);expected=f32(expected-post[2]) if post[2]>0 else expected
                if post[3]!=expected:raise ValueError('Withdrawal accepted total/ET return mismatch')
            self.water[key]['swu_return']=snapshot['WATER'];self.swu_calls+=1
        if tag=='WB_RETURN_STATE':
            if key not in self.water or self.water[key]['phase']!='flux' or key in self.swu:raise ValueError('Water return missing causal records')
            del self.water[key];self.water_calls+=1
        if tag=='DAY_CLOSE_STATE' and (key in self.water or key in self.swu):raise ValueError('Daily close with unconsumed causal owner')

    def finish(self):
        if self.water or self.swu or self.idat or self.ready_stores:raise ValueError('Unclosed causal owner')
        return dict(passed=True,water_calls=self.water_calls,withdrawal_calls=self.swu_calls)
