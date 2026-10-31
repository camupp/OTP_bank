"""Independent, read-only candidate desk-check. Writes only adjacent verification.json.
Does not execute/import either branch calculator or any sealed model.
Run from any directory: python3 <this file>.
"""
import csv, hashlib, json, math, re
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
from copy import deepcopy

O=Path(__file__).resolve().parent
R=O.parent.parent
def j(p): return json.loads((R/p).read_text())
def rows(p):
    with (R/p).open() as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256((R/p).read_bytes()).hexdigest()
def yes(x): return x is True or x=='True'
checks=[]
def ck(name,ok,detail=None):
    checks.append({'check':name,'pass':bool(ok),'detail':detail})
    if not ok: raise AssertionError(name+': '+str(detail))
frozen=j('private/versions-before-checks.json')
ck('candidate hashes',all(sha(p)==h for p,h in frozen.items()),len(frozen))
im=j('inputs/manifest.json')['files']; sm=j('supporting/manifest.json')
ck('inputs/supporting hashes',all(sha(base+'/'+p)==h for base,m in [('inputs',im),('supporting',sm)] for p,h in m.items()),len(im)+len(sm))
syn=j('supporting/synthetic-examples.json')
par=j('supporting/previous-best/finance-spec.json')
a=j('branches/A/finance-spec-011.json'); b=j('branches/B/finance-spec-015.json')
invariants=['envelope_R_year','currency','N_eligible','eligibility','lower_tier','special','stacking','annual_total_R','monthly_calendar_R','operational_metrics_assumptions','no_self_award_controls']
ck('common substantive invariants',all(p[k]==par[k] for p in [a,b] for k in invariants),invariants)
ck('A contests unchanged',a['contests']==par['contests'])
ck('B qualification unchanged',b['contests']['ranking']==par['contests']['ranking'])
ck('B four shares', [F(str(x['share_group_pool'])) for x in b['contests']['top_tiers']]==[F(4,10),F(3,10),F(2,10),F(1,10)])
for branch in ['A','B']:
    reuse=j('branches/'+branch+'/money-core-reuse.json')
    ck(branch+' reuse refs hashes',all(sha(x['path'])==x['sha256'] for x in reuse['references']),len(reuse['references']))

def evaluate(records,strata,days,family,sample):
    q=sum((F(s['mix_weight'])*sum(F(x['accepted_units']) for x in records if x['stratum']==sid)/F(s['hours'])/F(s['benchmark']) for sid,s in strata.items()),F(0))
    qa=sum((F(max(0,100-2*x['minor']-10*x['major'])) for x in sample),F(0))/len(sample)
    count=len(records); units=sum(F(x['accepted_units']) for x in records)
    ok=(count>=(8 if family=='IT_team' else 20) and days>=10 and qa>=(97 if family=='support' else 98)
        and not any(x['critical'] for x in records)
        and F(sum(x['reopened_or_returned'] for x in records),count)<=(F(2,100) if family=='backoffice' else F(5,100))
        and (family!='IT_team' or F(sum(x['sla_met'] for x in records),count)>=F(95,100))
        and (family=='IT_team' or units>=(100 if family=='support' else 80)))
    return q,qa,500 if ok and q>=1 else 0,ok and q>=F(11,10)

# Reconstruct A raw rows independently, including explicitly supplemental fixtures.
ac=j('branches/A/rawcase-calculations.json')['calculations']; amap={}; an=0
for d in ac:
    fam=d['family']; src=syn['families'][fam]; ident=d['id']; rec=deepcopy(src['records'])
    if ident.startswith('quality-'):
        n=int(ident.rsplit('n',1)[1]); rec=[]
        for i in range(n):
            x=deepcopy(src['records'][i%len(src['records'])]); x.update(case_id=f'controlled-{i+1}',stratum='s1' if i<n//2 else 's2',accepted_units=max(10,x['accepted_units']));rec.append(x)
    if ident=='QA97':
        for i,x in enumerate(rec):x['minor']=2 if i<10 else 1
    for x in rec:x['case_id']=ident+'::'+x['case_id']
    benefit=ident+'::'+src['benefit_id']
    hashfn=lambda x:hashlib.sha256(','.join([src['window_id'],benefit,x['case_id'],src['qa_seed']]).encode()).hexdigest()
    sample=rec if len(rec)<=20 else sorted(rec,key=hashfn)[:20]
    if ident=='critical-outside-sample' and d['critical_all_registry']:
        outside=next(x for x in rec if x['case_id'] not in {z['case_id'] for z in sample});outside['critical']=True
    st={x['stratum']:{'mix_weight':x['mix_weight'],'hours':x['productive_hours'],'benchmark':x['benchmark']} for x in d['strata']}
    for sid,s in st.items():
        units=sum(F(x['accepted_units']) for x in rec if x['stratum']==sid)
        ck('A stratum '+ident+'/'+sid,units==F(next(z['accepted_standard_units'] for z in d['strata'] if z['stratum']==sid)))
        multiplier=F(d['locator'].rsplit('=',1)[1])
        controlled=ident.startswith('quality-') or ident in ['QA97','critical-outside-sample'] and d['critical_all_registry'] or ident=='QA97'
        hours=(units/F(s['benchmark']) if controlled else F(src['strata'][sid]['base_productive_hours']))/multiplier
        ck('A hours '+ident+'/'+sid,F(s['hours'])==hours)
    q,qa,lo,top=evaluate(rec,st,d['days'],fam,sample)
    ck('A Q/QA/rights '+ident,q==F(d['Q_exact']) and float(qa)==d['QA_mean'] and lo==d['lower_R'] and top==d['top_eligible'] and [x['case_id'] for x in sample]==d['sample_case_ids'])
    amap[benefit]=d;an+=len(rec)

# B stores each expanded raw row, allowing independent hash/sample/strata reproduction.
br=rows('branches/B/rawcases-expanded.csv'); bs=rows('branches/B/strata-calculation.csv'); bq=rows('branches/B/synthetic-results.csv')
rg=defaultdict(list);sg=defaultdict(dict)
for x in br:
    y=dict(x)
    for k in ['minor','major']:y[k]=int(y[k])
    for k in ['critical','reopened_or_returned','sla_met']:y[k]=yes(y[k])
    rg[x['scenario_id']].append(y)
for x in bs:sg[x['scenario_id']][x['stratum']]={'mix_weight':x['mix_weight'],'hours':x['productive_hours_exact'],'benchmark':x['benchmark_units_hour'],'units':x['accepted_standard_units'],'component':x['Q_component_exact']}
for d in bq:
    ident=d['scenario_id']; rec=rg[ident]
    src=syn['families'][d['family']];srcmap={x['case_id']:x for x in src['records']}
    for x in rec:
        h=hashlib.sha256('|'.join([x['window_id'],x['benefit_id'],x['case_id'],x['seed']]).encode()).hexdigest()
        ck('B raw SHA '+ident+'/'+x['case_id'],h==x['qa_hash'] and int(x['score'])==max(0,100-2*x['minor']-10*x['major']))
        template=srcmap[x['source_case_id']]
        ck('B shared raw values '+ident+'/'+x['case_id'],all(str(x[k])==str(template[k]) for k in ['stratum','accepted_units','reopened_or_returned','sla_met']))
    sample=sorted(rec,key=lambda x:x['qa_hash'])[:min(20,len(rec))]
    ck('B sample '+ident,{x['case_id'] for x in sample}=={x['case_id'] for x in rec if yes(x['selected_QA'])}==set(d['sample_IDs'].split(';')))
    for sid,s in sg[ident].items():
        units=sum(F(x['accepted_units']) for x in rec if x['stratum']==sid)
        ck('B stratum '+ident+'/'+sid,units==F(s['units']) and F(s['component'])==F(s['mix_weight'])*units/F(s['hours'])/F(s['benchmark']))
        profile=next((p for p in syn['Q_profiles'] if ident.endswith(':'+p['profile'])),None)
        if re.fullmatch('I[0-9]+',ident):multiplier=F(syn['individual_group_40']['multipliers'][int(ident[1:])-1])
        elif re.fullmatch('T[0-9]+',ident):multiplier=F(syn['team_group_40']['multipliers'][int(ident[1:])-1])
        else:multiplier=F(profile['productivity_multiplier']) if profile else F(6,5)
        ck('B hours '+ident+'/'+sid,F(s['hours'])==F(src['strata'][sid]['base_productive_hours'])/multiplier)
    q,qa,lo,top=evaluate(rec,sg[ident],int(d['exposure_days']),d['family'],sample)
    ck('B Q/QA/rights '+ident,q==F(d['Q_exact']) and qa==F(d['QA_exact']) and lo==int(d['lower_R']) and top==yes(d['top_eligible']))

# Independent allocation by exact rank, tying occupied slots, then personal floor.
def allocations(units,n,slots):
    out={k:F(0) for k in units}; ranks=defaultdict(list)
    for k,v in units.items():
        if v['top']:ranks[math.floor(F(v['q'])*100+F(1,2))].append(k)
    pos=0
    for rank in sorted(ranks,reverse=True):
        ids=ranks[rank]; val=250*n*sum(slots[pos:pos+len(ids)],F(0))/len(ids) if len(units)>1 else F(0)
        for k in ids:out[k]=val
        pos+=len(ids)
    return out
old=[F(4,5),F(1,5)];new=[F(2,5),F(3,10),F(1,5),F(1,10)]
am=rows('branches/A/money-examples.csv'); ag=defaultdict(list)
for x in am:ag[x['scenario']].append(x)
for scenario,rr in ag.items():
    if scenario in ['profiles','quality_n','exposure','QA97_backoffice','critical','special']:continue
    n={'teams3and7':10,'ineligible_member_share':10,'group1':1,'group2':2,'group5':5,'group60':60}.get(scenario,40)
    units={x['benefit_id']:{'q':amap[x['benefit_id']]['Q_exact'],'top':amap[x['benefit_id']]['top_eligible']} for x in rr}
    amounts=allocations(units,n,old)
    for x in rr:
        expected=math.floor(amounts[x['benefit_id']]*F(x['FTE_share'])) if int(x['candidate_lower_R']) else 0
        ck('A payout '+scenario+'/'+x['participant'],int(x['candidate_top_R'])==expected==int(x['parent_top_R']) and x['parent_right_date']==x['candidate_right_date'])
ck('A all445 lower/top/special/date equal',len(am)==445 and all(all(x['parent_'+k+'_R']==x['candidate_'+k+'_R'] for k in ['lower','top','special']) and x['parent_right_date']==x['candidate_right_date'] for x in am))
bm=rows('branches/B/money-examples.csv'); bg=defaultdict(list)
for x in bm:bg[x['group']].append(x)
for group,rr in bg.items():
    units={x['unit_id']:{'q':x['Q_exact'],'top':yes(x['qualified_top'])} for x in rr}
    for slots,col in [(old,'old_person_top_R'),(new,'new_person_top_R')]:
        amounts=allocations(units,40,slots)
        ck('B payout '+group+'/'+col,all(int(x[col])==math.floor(amounts[x['unit_id']]*F(x['FTE_share'])) for x in rr))
be=rows('branches/B/edge-cases.csv');eg=defaultdict(list)
for x in be:eg[x['scenario']].append(x)
for name,rr in eg.items():
    units={x['unit_id']:{'q':x['Q'] or '0','top':bool(x['Q']) and F(x['Q'])>=F(11,10)} for x in rr}
    for slots,col in [(old,'old_top_R'),(new,'new_top_R')]:
        amounts=allocations(units,int(rr[0]['n_people']),slots)
        ck('B edge '+name+'/'+col,all(int(x[col])==(math.floor(amounts[x['unit_id']]*F(x['share'])) if yes(x['personal_pass']) else 0) for x in rr))

# Common fixture comparability: SHA/IDs differ, homogeneous QA98 means identical rights.
comparison=[]
for i in range(40):
    ad=amap['support-person'+str(i+1).zfill(2)+'::support-unique-benefit'];bd=next(x for x in bq if x['scenario_id']=='I'+str(i+1).zfill(2))
    aset={x.split('::')[-1] for x in ad['sample_case_ids']};bset={x.split(':')[-1] for x in bd['sample_IDs'].split(';')}
    comparison.append({'person':i+1,'sample_same_template_cases':aset==bset,'overlap_cases':len(aset&bset),'Q_equal':F(ad['Q_exact'])==F(bd['Q_exact']),'QA_equal':ad['QA_mean']==float(bd['QA_mean']),'eligibility_equal':ad['lower_R']==int(bd['lower_R']) and ad['top_eligible']==yes(bd['top_eligible'])})
ck('comparable forty current outcomes',all(x['Q_equal'] and x['QA_equal'] and x['eligibility_equal'] for x in comparison))
ck('critical outside sample A',next(x for x in ac if x['id']=='critical-outside-sample' and x['critical_all_registry'])['lower_R']==0)
crit=rg['support:criticalOutside'];ck('critical outside sample B',any(x['critical'] and not yes(x['selected_QA']) for x in crit) and next(x for x in bq if x['scenario_id']=='support:criticalOutside')['lower_R']=='0')
summary={'classification':'Synthetic independent desk-check; not measured employee understanding or bank readiness','candidate_hashes':frozen,'hashes_rechecked_after':all(sha(p)==h for p,h in frozen.items()),'inputs_supporting_hashes':{base+'/'+p:h for base,m in [('inputs',im),('supporting',sm)] for p,h in m.items()},'counts':{'checks':len(checks),'A_assessments':len(ac),'A_reconstructed_raw_rows':an,'A_money_rows':len(am),'B_assessments':len(bq),'B_raw_rows':len(br),'B_money_rows':len(bm),'B_edge_rows':len(be)},'checks':checks,'common_fixture_SHA_comparison':comparison,'sample_formats':{'A':'UTF8 comma-join; prefix::caseID and prefix::benefitID','B':'UTF8 pipe-join; prefix:caseID and prefix:benefitID','interpretation':'Explicit deterministic implementations of an underspecified parent encoding; different samples, same current comparable QA98/Q/rights. Not evidence of interchangeable results on heterogeneous bank errors.'},'not_repeated':['54220 earlier quality boundaries','full money/stock/36-month/tail grid','source-library reading','web search','raw diagnosis'],'candidate_generators_executed':False,'modified_inputs_candidates_registries':False}
(O/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['counts','hashes_rechecked_after']},ensure_ascii=False))
