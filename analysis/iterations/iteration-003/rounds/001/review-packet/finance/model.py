"""Four-version finance check; stdlib. Reimplements flows from frozen M01.
M02 procurement/region layer is new; no candidate model is imported/executed.
"""
import csv,json,math,re,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROUND=OUT.parent.parent
ROOT=OUT.parents[6]
EPS=1e-5
KEYS=['V03','V02','V04','V01']
POLICIES={
 'V03':dict(hr=0,other=0,jmonth=0,jfirst=0,hrfirst=0,it_once=0,it_month=0,research_once=0,research_month=0,training=0,manager=None,hrcap=None,rcap=None),
 'V02':dict(hr=40,other=126.66666666666667,jmonth=0,jfirst=0,hrfirst=0,it_once=0,it_month=0,research_once=0,research_month=0,training=0,manager=86.66666666666667,hrcap=600000,rcap=3000000,I_C_per_year=48000000,F_grant_per_quarter_R=0,R_awarded_per_quarter=0),
 'V04':dict(hr=24,other=380,jmonth=1200,jfirst=0,hrfirst=0,it_once=240,it_month=8,research_once=80,research_month=8,training=0,manager=220,hrcap=600000,rcap=3000000,I_C_per_year=0,F_grant_per_quarter_R=0,R_awarded_per_quarter=0),
 'V01':dict(hr=36,other=204,jmonth=600,jfirst=7200,hrfirst=16,it_once=160,it_month=8,research_once=100,research_month=0,training=915,manager=124,hrcap=750000,rcap=3000000,I_C_per_year=0,F_grant_per_quarter_R=0,R_awarded_per_quarter=0)
}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x): (OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvout(n,rows):
 with (OUT/n).open('w',newline='') as f:
  w=csv.DictWriter(f,list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:round(v,7) if isinstance(v,float) else v for k,v in r.items()})
def take(q,cap):
 out=0
 while q and cap>EPS:
  tag,value=q[0];a=min(value,cap);out+=a;cap-=a
  if value-a<EPS:q.pop(0)
  else:q[0]=(tag,value-a)
 return out
qsum=lambda q:sum(v for _,v in q)
def replenish(demands,opening,mode):
 stock=list(opening);rows=[]
 targets=[600,400]
 for m,ds in enumerate(demands,1):
  r=[]
  for s,d in enumerate(ds):
   receipt=max(0,math.ceil((targets[s]+d-stock[s]-EPS)/500))*500 if mode else d
   close=stock[s]+receipt-d
   assert close>=-EPS
   r.append((stock[s],receipt,close));stock[s]=close
  rows.append(r)
 return rows

def run(m01,key,scenario,mode='M01',year=1,opening=None,fullnew=False,merch=False,skew=False):
 p=dict(m01['common'],**scenario['overrides']);pol=POLICIES[key]
 p.update({k:v for k,v in pol.items() if k in p})
 if opening:
  p.update(C0=opening['C_close'],R0=opening['R_close'],opening_supplier_payables_rub=opening['AP_actual_close_rub'])
 if fullnew:p['C_new_request_fraction']=1
 if merch:p['basket_cost_to_nominal']=0.76
 shares=[0.3,0.7] if skew else [0.6,0.4]
 caps=[1800,1200] if mode=='M02' else [p['basket_delivery_capacity_units_per_month']*x for x in shares]
 C,R,F,J=p['C0'],p['R0'],p['F0'],opening['J_close'] if opening else 0
 aq=[list(map(tuple,x)) for x in opening['_C_queues']] if opening else [[],[]]
 jq=[x for x in opening['_J_queues']] if opening else [0,0]
 rq=list(map(tuple,opening['_R_queue'])) if opening else []
 Cfree=C-sum(map(qsum,aq));Rfree=R-qsum(rq)
 weights=[1/12]*12 if p['old_requests_calendar']=='uniform' else [0.5]+[0.5/11]*11
 weights[-1]=1-sum(weights[:-1]);A=B=C/2
 rows=[];errors=[]
 for m,w in enumerate(weights,1):
  cs,rs,fs,js=C,R,F,J
  G=p['F_grant_per_quarter_R'] if m%3==1 else 0
  W=p['R_awarded_per_quarter']*p['R_award_month_shares_in_quarter'][(m-1)%3]
  F+=G-W;expired=F if m%3==0 else 0;F-=expired
  I=p['I_C_per_year']/12
  X=(Rfree*w+W)*p['R_conversion_fraction_old_and_new']
  dcold=Cfree*w*p['C_old_request_fraction'];dcnew=I*p['C_new_request_fraction'];dcconv=X*p['converted_C_request_fraction'];dc=dcold+dcnew+dcconv
  dr=(Rfree*w+W)*p['R_direct_fraction_old_and_new']
  C+=I+X;R+=W-X
  if key=='V01':created=7200 if year==1 and m==1 else 0 if year==1 else 600
  else:created=pol['jmonth']
  J+=created;due=pol['jmonth']
  pc=0;servedj=0;region_required=[];region_actual=[];regionc=[];regionj=[]
  for s,sh in enumerate(shares):
   aq[s].extend([('old',dcold*sh),('new',dcnew*sh),('converted',dcconv*sh)])
   jq[s]+=due*sh
   c=take(aq[s],caps[s]*p['basket_C_price']);j=min(jq[s],max(0,caps[s]-c/p['basket_C_price']))
   jq[s]-=j;pc+=c;servedj+=j
   region_required.append((dc/p['basket_C_price']+due)*sh);region_actual.append(c/p['basket_C_price']+j)
   regionc.append(qsum(aq[s]));regionj.append(jq[s])
  rq.append(('R',dr));pr=take(rq,p['R_direct_capacity_units_per_month']*p['R_direct_price_per_unit'])
  C-=pc;R-=pr;J-=servedj
  # Synthetic two pools only; allocate redemption proportionally after transfers.
  A+=(I+X)/2;B+=(I+X)/2
  ta=p['C_transfer_A_to_B_per_month'];tb=p['C_transfer_B_to_A_per_month']
  transfer_feasible=A>=ta-EPS and B+ta>=tb-EPS
  if transfer_feasible:A+=tb-ta;B+=ta-tb
  total=A+B
  if total>EPS:A-=pc*A/total;B-=pc*B/total
  else:assert pc<EPS
  baskets=sum(region_required);actual=sum(region_actual);services=dr/p['R_direct_price_per_unit']
  sharemerch=0.8 if merch else p['basket_merch_nominal_share'];log=baskets*sharemerch*150 if mode=='M02' else 0
  logactual=actual*sharemerch*150 if mode=='M02' else 0
  hr=p['admin_fixed_hours_per_month']+p['admin_hours_per_basket']*baskets+p['admin_hours_per_R_direct_unit']*services+pol['hr']+(pol['hrfirst'] if year==1 and m==1 else 0)+(baskets*sharemerch*2/60 if mode=='M02' else 0)
  other=pol['other']+pol['it_month']+pol['research_month']
  if year==1 and m==1:other+=pol['it_once']+pol['research_once']+pol['training']
  rr=services*p['R_direct_hours_per_unit']*p['resource_rub_per_hour'];rc=rr*p['R_direct_cash_share_of_resource'];hrres=hr*p['resource_rub_per_hour'];hrcash=hrres*p['admin_cash_share_of_resource']
  errs=[abs(C-cs-I-X+pc),abs(R-rs-W+X+pr),abs(F-fs-G+W+expired),abs(J-js-created+servedj),abs(A+B-C),abs(C+R+F-cs-rs-fs-I-G+pc+pr+expired)]
  errors.extend(errs)
  assert min(C,R,F,J,A,B)>=-EPS and max(errs)<EPS
  assert sum(regionc)<=C+EPS and qsum(rq)<=R+EPS and sum(regionj)<=J+EPS
  row=dict(candidate_key=key,scenario=(mode+'_'+scenario['id'])+('_MERCH' if merch else '')+('_REGION' if skew else '')+('_FULL_NEW' if fullnew else ''),year=year,month=m,C_open=cs,R_open=rs,F_open=fs,J_open=js,I_C=I,G_R=G,W_R=W,conversion_R_to_C=X,C_requested=dc,R_requested=dr,C_redeemed=pc,R_redeemed=pr,F_expired=expired,C_close=C,R_close=R,F_close=F,C_queue_close=sum(regionc),R_queue_close=qsum(rq),C_pool_A=A,C_pool_B=B,C_transfer_A_to_B=ta if transfer_feasible else 0,C_transfer_B_to_A=tb if transfer_feasible else 0,synthetic_transfer_feasible=transfer_feasible,J_created=created,J_due=due,J_served=servedj,J_close=J,J_overdue=sum(regionj),J_admission_cap_conflict=key=='V04' and js+created>2400+EPS,basket_units_required=baskets,basket_units_actual=actual,R_units_required=services,R_units_actual=pr/p['R_direct_price_per_unit'],region1_required=region_required[0],region2_required=region_required[1],region1_actual=region_actual[0],region2_actual=region_actual[1],logistics_required_rub=log,logistics_actual_rub=logactual,HR_hours=hr,HR_resource_rub=hrres,HR_cash_rub=hrcash,R_hours_required=services*p['R_direct_hours_per_unit'],R_resource_required_rub=rr,R_cash_required_rub=rc,other_internal_hours=other,other_internal_resource_rub=other*p['resource_rub_per_hour'],manager_hours=pol['manager'] if pol['manager'] is not None else -1,manager_capacity100_pass=pol['manager']<=100 if pol['manager'] is not None else 'unknown',manager_capacity300_pass=pol['manager']<=300 if pol['manager'] is not None else 'unknown')
  row['_req']=region_required;row['_actual']=region_actual;rows.append(row)
 # Required and actual delivery plans receive equal cost/stock/lag assumptions.
 reqopen=opening['_reqstock'] if opening and mode=='M02' else [600,400]
 actopen=opening['_actstock'] if opening and mode=='M02' else [600,400]
 reqs=replenish([x['_req'] for x in rows],reqopen,mode=='M02');acts=replenish([x['_actual'] for x in rows],actopen,mode=='M02')
 cost=p['basket_nominal_rub']*p['basket_cost_to_nominal']*p['purchase_price_multiplier'];lag=p['procurement_next_month_payment_fraction'];same=p['procurement_same_month_payment_fraction']
 prevreq=prevact=0
 for i,row in enumerate(rows):
  req,act=reqs[i],acts[i]
  for s in [0,1]:
   for suffix,seq in [('required',req),('actual',act)]:
    op,receipt,cl=seq[s];row[f'region{s+1}_stock_{suffix}_open']=op;row[f'region{s+1}_receipt_{suffix}']=receipt;row[f'region{s+1}_stock_{suffix}_close']=cl
    row[f'region{s+1}_receipt_order_placed_month']=row['month']-1
    errors.append(abs(op+receipt-row['_req' if suffix=='required' else '_actual'][s]-cl))
  preq=sum(x[1] for x in req)*cost;pact=sum(x[1] for x in act)*cost
  due=p['opening_supplier_payables_rub'] if i==0 else 0
  row.update(procurement_required_rub=preq,procurement_actual_rub=pact,reward_cash_required_rub=due+same*preq+lag*prevreq+row['logistics_required_rub'],reward_cash_actual_rub=due+same*pact+lag*prevact+row['logistics_actual_rub'],AP_required_open_rub=due+lag*prevreq,AP_actual_open_rub=due+lag*prevact,AP_required_close_rub=lag*preq,AP_actual_close_rub=lag*pact)
  row['narrow_cost_required_rub']=preq+row['logistics_required_rub'];row['narrow_cost_actual_rub']=pact+row['logistics_actual_rub']
  row['all_cash_required_rub']=row['reward_cash_required_rub']+row['HR_cash_rub']+row['R_cash_required_rub']
  row['goods_consumption_resource_required_rub']=row['basket_units_required']*cost
  row['goods_consumption_resource_actual_rub']=row['basket_units_actual']*cost
  row['scoped_resource_cost_required_rub']=row['goods_consumption_resource_required_rub']+row['logistics_required_rub']+row['HR_resource_rub']+row['R_resource_required_rub']+row['other_internal_resource_rub']
  errors.append(abs(row['reward_cash_required_rub']-row['logistics_required_rub']-row['AP_required_open_rub']-preq+row['AP_required_close_rub']))
  errors.append(abs(row['reward_cash_actual_rub']-row['logistics_actual_rub']-row['AP_actual_open_rub']-pact+row['AP_actual_close_rub']))
  prevreq,prevact=preq,pact
  del row['_req'];del row['_actual']
 totals=['I_C','G_R','W_R','conversion_R_to_C','C_requested','R_requested','C_redeemed','R_redeemed','F_expired','J_created','J_due','J_served','basket_units_required','basket_units_actual','R_units_required','R_units_actual','procurement_required_rub','procurement_actual_rub','logistics_required_rub','logistics_actual_rub','narrow_cost_required_rub','narrow_cost_actual_rub','reward_cash_required_rub','reward_cash_actual_rub','HR_hours','HR_resource_rub','HR_cash_rub','R_hours_required','R_resource_required_rub','R_cash_required_rub','other_internal_hours','other_internal_resource_rub','all_cash_required_rub','scoped_resource_cost_required_rub']
 a=dict(candidate_key=key,scenario=rows[0]['scenario'],year=year,C_open=p['C0'],R_open=p['R0'],J_open=rows[0]['J_open'],AP_open_rub=p['opening_supplier_payables_rub'],**{k:sum(r[k] for r in rows) for k in totals})
 for k in ['C_close','R_close','F_close','J_close','C_queue_close','R_queue_close','J_overdue','C_pool_A','C_pool_B','AP_required_close_rub','AP_actual_close_rub']+[f'region{s}_stock_{t}_close' for s in [1,2] for t in ['required','actual']]:a[k]=rows[-1][k]
 for k in ['basket_units_required','R_units_required','HR_hours','C_queue_close','R_queue_close','J_overdue','region1_required','region2_required']:a['peak_'+k]=max(r[k] for r in rows)
 a['capacity_pass']=all(r['region1_required']<=caps[0]+EPS and r['region2_required']<=caps[1]+EPS and r['R_units_required']<=p['R_direct_capacity_units_per_month']+EPS and r['HR_hours']<=p['admin_capacity_hours_per_month']+EPS for r in rows)
 a['timely_service_pass']=all(r['C_queue_close']<EPS and r['R_queue_close']<EPS and r['J_overdue']<EPS for r in rows)
 a['full_new_rights_pass']=a['J_served']>=a['J_due']-EPS
 a['manager_capacity100_pass']=rows[0]['manager_capacity100_pass'];a['manager_capacity300_pass']=rows[0]['manager_capacity300_pass']
 a['external_cash_envelope_pass']=a['HR_cash_rub']<=pol['hrcap']+EPS and a['R_cash_required_rub']<=pol['rcap']+EPS if pol['hrcap'] is not None else 'not_specified'
 for b in [30000000,34000000]:a[f'narrow_budget_{b}_pass']=max(a['narrow_cost_required_rub'],a['reward_cash_required_rub'])<=b+EPS;a[f'headroom_{b}_rub']=b-max(a['narrow_cost_required_rub'],a['reward_cash_required_rub'])
 a['opening_stock_value_rub']=sum(reqopen)*cost;a['closing_stock_value_rub']=sum(x[2] for x in reqs[-1])*cost
 a['goods_consumption_resource_required_rub']=sum(r['goods_consumption_resource_required_rub'] for r in rows)
 a['goods_consumption_resource_actual_rub']=sum(r['goods_consumption_resource_actual_rub'] for r in rows)
 a['inventory_asset_change_rub']=a['closing_stock_value_rub']-a['opening_stock_value_rub']
 errors.append(abs(a['procurement_required_rub']-a['inventory_asset_change_rub']-a['goods_consumption_resource_required_rub']))
 # Next-Jan orders placed in Dec for the same demand/price illustration; future commitment, not receipt/AP/cash now.
 if mode=='M02':
  projected=((C-sum(map(qsum,aq)))*p['C_old_request_fraction']+(R-qsum(rq))*p['R_conversion_fraction_old_and_new']*p['converted_C_request_fraction'])/p['basket_C_price']/12+p['I_C_per_year']/12*p['C_new_request_fraction']/p['basket_C_price']+pol['jmonth']
  if key=='V03':projected+=p['R_awarded_per_quarter']*p['R_award_month_shares_in_quarter'][0]*p['R_conversion_fraction_old_and_new']*p['converted_C_request_fraction']/p['basket_C_price']
  nextq=[max(0,math.ceil((t+projected*sh-s[2]-EPS)/500))*500 for t,sh,s in zip([600,400],shares,acts[-1])]
 else:nextq=[0,0]
 a['closing_PO_next_January_units']=sum(nextq);a['closing_PO_commitment_rub']=sum(nextq)*cost
 a['opening_PO_January_units']=sum(x[1] for x in reqs[0]) if mode=='M02' else 0
 a['opening_PO_January_commitment_rub']=a['opening_PO_January_units']*cost
 a['max_reconciliation_error']=max(errors);assert max(errors)<EPS
 a['_C_queues']=aq;a['_J_queues']=jq;a['_R_queue']=rq;a['_reqstock']=[x[2] for x in reqs[-1]];a['_actstock']=[x[2] for x in acts[-1]]
 return a,rows

def main():
 manifest=json.loads((ROUND/'inputs/manifest.json').read_text())
 assert all(sha(ROUND/'inputs'/n)==h for n,h in manifest['files'].items())
 ctx=(ROUND/'inputs/context.md').read_text();m01=json.loads(re.search(r'### Полные общие параметры M01\s+```json\s+(.*?)\s+```',ctx,re.S).group(1))
 paths={'V03':ROUND/'inputs/baseline.md','V02':ROOT/'candidates/V02.md','V04':ROUND/'candidates/V04.md','V01':ROUND/'candidates/V01.md'}
 hashes={str(p.relative_to(ROOT)):sha(p) for p in paths.values()}
 annual=[];monthly=[];idx={}
 for key in KEYS:
  for mode in ['M01','M02']:
   for scen in m01['scenarios']:
    a,rs=run(m01,key,scen,mode);annual.append(a);monthly+=rs;idx[(key,a['scenario'],1)]=a
   prev=idx[(key,mode+'_CORE',1)]
   for y in range(2,6):
    a,rs=run(m01,key,m01['scenarios'][0],mode,y,prev);annual.append(a);monthly+=rs;idx[(key,a['scenario'],y)]=a;prev=a
  for kwargs in [dict(merch=True),dict(skew=True),dict(fullnew=True)]:
   a,rs=run(m01,key,m01['scenarios'][0],'M02',**kwargs);annual.append(a);monthly+=rs;idx[(key,a['scenario'],1)]=a
 clean=[{k:v for k,v in r.items() if not k.startswith('_')} for r in annual]
 csvout('annual-results.csv',clean);csvout('monthly-results.csv',monthly)
 dump('annual-results.json',clean)
 dump('model-inputs.json',{'M01':m01,'policies':POLICIES,'M02':{'regions_demand':[0.6,0.4],'regions_capacity':[1800,1200],'regions_opening_target_stock':[600,400],'batch_per_region':500,'lead_months':1,'merch_logistics_rub_unit':150,'merch_manual_minutes_unit':2,'payment_terms':'75%receipt month/25%next; no prepayment in CORE','forecast':'Known scenario demand used for preorders; not proven forecasting accuracy','shipping':'150 per delivered merchandise unit, additional stock not yet shipped is stock value/commitment, not free'},'candidate_hashes':hashes,'source_model_reused_as_formula_reference':'iteration-002 checks/finance/model.py; not executed/imported','frozen_fingerprint':manifest['fingerprint']})
 checks={'status':'pass','annual_rows':len(clean),'monthly_rows':len(monthly),'max_reconciliation_error':max(a['max_reconciliation_error'] for a in annual),'candidate_hashes':hashes,'checks':['five frozen hashes','C/R/F/J monthly stock-flow','internal transfers zero emission and pools nonnegative','queues included within C/R/J','regional demand/capacity and separate queues','regional inventory: opening+receipts-delivery=closing','batch multiples500; placed previous month','AP and cash monthly, required vs actual','opening stock and prior orders disclosed','closing stock/AP/PO carried to later CORE years','full new J issuance/redemption, no assumed virtual relief','both30m/34m budgets and full-demand costing'],'limitations':['No actual bank ledger/catalog/contract/resource approval','Fractional normalized basket; not SKU-specific assortment forecast','CORE assumes known demand and preorders, no supplier prepayment; delay/forecast error outside admission','Baseline and specification have unpriced/unquantified internal work; scoped cost is incomplete','After failed service in stresses, continuation is diagnostic, not an implementable forecast','No employee-level calendar or legal/tax validation']}
 dump('validation.json',checks)
 print(json.dumps({'status':checks['status'],'annual_rows':len(clean),'monthly_rows':len(monthly),'max_error':checks['max_reconciliation_error']}))
 return m01,idx
if __name__=='__main__': main()
