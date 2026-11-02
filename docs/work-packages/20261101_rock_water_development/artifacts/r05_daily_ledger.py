"""Daily endpoint accounting from explicit R05 native owners, in meters."""
from fractions import Fraction as F
import struct


def f32(x):return struct.unpack('>f',struct.pack('>f',x))[0]


def ledger(inputs,outputs,start,end):
    if set(inputs)!={'rain','melt','irrigation','furrow','surface_runon','subsurface_runon'} or set(outputs)!={'surface','lateral','deep','plant_et','soil_et','residue_et','tile'} or set(start)!={'soil_liquid','soil_ice','canopy','residue'} or set(end)!=set(start):
        raise ValueError('Missing or duplicated water ownership component')
    flux=sum(map(F,inputs.values()))-sum(map(F,outputs.values()))
    delta=sum(map(F,end.values()))-sum(map(F,start.values()))
    return dict(net_flux_m_exact=str(flux),store_change_m_exact=str(delta),residual_m_exact=str(flux-delta),
                requires_interpretation=flux!=delta,scientific_acceptance=False,
                scope='Recorded soil, canopy and residue ledger; RM already contains melt, so snow stock is separate.')


def stocks(state):
    water=state['WATER'];frdp=water['frdp(ip)']
    if water['plaint(ip)']!=0:raise ValueError('Daily endpoint retains active PLAINT; adding carry would duplicate ownership')
    liquid=F(0);ice=F(0)
    for layer in state['LAYER']:
        computed_liquid=f32(layer['st(j,ip)']+f32(layer['thetdr(j,ip)']*f32(layer['dg(j,ip)']-layer['frozen(j,ip)'])))
        computed_ice=f32(layer['frzw(j,ip)']+f32(layer['thetdr(j,ip)']*layer['frozen(j,ip)'])) if frdp>f32(.001) else 0.
        if layer['soilw(j,ip)']!=computed_liquid or layer['soilf(j,ip)']!=computed_ice:
            raise ValueError('Daily cached stock differs from contemporaneous native layer representation')
        liquid+=F(layer['soilw(j,ip)']);ice+=F(layer['soilf(j,ip)'])
    return dict(soil_liquid=liquid,soil_ice=ice,canopy=F(water['pintlv(ip)']),residue=F(water['resint(ip)']))


class Daily:
    def __init__(self):
        self.states={};self.flux={};self.mode={};self.results=[];self.previous={}

    def consume(self,row):
        key=(row['year'],row['day'],row['ofe']);tag=row['tag'];v=row['values']
        if tag=='WB_DAILY_FLUX':self.flux.setdefault(key,[]).append(row)
        if tag=='WB_DAILY_MODE':self.mode.setdefault(key,[]).append(v[0])
        stage=row['snapshot']
        if stage not in ('DAY_OPEN','DAY_CLOSE'):return
        state=self.states.setdefault((key,stage),{'LAYER':[]})
        values=dict(zip(row['fields'],v))
        if row['group']=='LAYER':state['LAYER'].append(values)
        else:state[row['group']]=values
        if row['group']!='STATE':return
        current=stocks(state)
        if stage=='DAY_OPEN':
            previous=self.previous.get(row['ofe'])
            state['previous_close_equal']=previous is None or current==previous
            return
        start=self.states.pop((key,'DAY_OPEN'));before=stocks(start)
        self.previous[row['ofe']]=current
        fluxes=self.flux.pop(key,[]);modes=self.mode.pop(key,[])
        if not fluxes or len(fluxes)!=len(modes):raise ValueError('Missing daily flux/mode owner')
        result=dict(year=key[0],day=key[1],ofe=key[2],flux_invocations=len(fluxes),
                    previous_close_equal=start['previous_close_equal'],
                    start_stores_m_exact={k:str(v) for k,v in before.items()},end_stores_m_exact={k:str(v) for k,v in current.items()},
                    snow_start_m_exact=str(F(start['WATER']['snodpy(ip)'])*F(start['WATER']['densg(ip)'])/1000),
                    snow_end_m_exact=str(F(state['WATER']['snodpy(ip)'])*F(state['WATER']['densg(ip)'])/1000),
                    scientific_acceptance=False)
        if len(fluxes)==1:
            row=fluxes[0];fields=dict(zip(row['fields'],row['values']))
            get=lambda name:F(fields[name])
            if get('slplen(iplane)')<=0:raise ValueError('Nonpositive local water-balance geometry')
            surface=get('runoff(iplane)') if modes[0]!=0 else get('runoff(iplane)')*get('efflen(iplane)')/get('slplen(iplane)')
            inputs=dict(zip(('rain','melt','irrigation','furrow','surface_runon','subsurface_runon'),map(get,('rain(iplane)','wmelt(iplane)','irdept(iplane)','iraplo(iplane)','runoffin(iplane)','subrin'))))
            outputs=dict(surface=surface,**dict(zip(('plant_et','soil_et','residue_et','deep','lateral','tile'),map(get,('ep(iplane)','es(iplane)','eres(iplane)','sep(iplane)','sbrunf(iplane)','drainq(iplane)')))))
            result.update(ledger(inputs,outputs,before,current),flux_source_sequence=row['seq'],
                          inputs_m_exact={k:str(v) for k,v in inputs.items()},outputs_m_exact={k:str(v) for k,v in outputs.items()},
                          geometry_basis='Exact rational local/effective length conversion over observed native REALs; not a rounded WAT serialization certificate.')
        else:
            result.update(requires_interpretation=True,scope='Multiple daily flux invocations preserved; no assumption that cumulative reports are additive.')
        self.results.append(result);del self.states[(key,'DAY_CLOSE')]

    def finish(self):
        if self.states or self.flux or self.mode:raise ValueError('Unclosed daily ledger owner')
        return self.results
