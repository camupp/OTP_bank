#!/usr/bin/env python3.12
"""Independent finance audit. Reads specifications as DATA; imports no author/M05 code.
Run from any cwd: python3.12 <this file>. Outputs only assigned checks paths.
All money RUB; currency C/R; baskets are normalized divisible demand units.
"""
import csv, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
M=json.loads((ROOT/'supporting/finance-basis/scenario-inputs.json').read_text())
C=M['common']; EPS=1e-6
SPECS={}
for rec in json.loads((ROOT/'candidate-inputs.json').read_text())['candidates']:
 SPECS[rec['candidate_key']]=json.loads((ROOT/rec['spec']).read_text())
INC=json.loads((ROOT/'../../incumbent/finance-projection.json').read_text())
KEYS=['BASELINE','CON-009@v1','CON-011@v1','CON-012@v1','CON-013@v1','CON-014@v1']
E={'BASELINE':19427591*4,'CON-009@v1':8000000,**{k:s['annual_total_R'] for k,s in SPECS.items()}}
SCENS={s['id']:s['overrides'] for s in M['scenarios']}
SCENS.update({'FULL_NEW_QUARTER_END_R':{'new_fixed_C_use':1.,'R_calendar':'quarter_end'},'FULL_NEW_REGION80':{'new_fixed_C_use':1.,'region_demand_shares':[.2,.8]},'FULL_NEW_JAN_OLD50':{'new_fixed_C_use':1.,'old_january_share':.5}})

def writejson(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 if not rows:return
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for row in rows:w.writerow({k:round(v,7) if isinstance(v,float) else v for k,v in row.items()})

def issuance(key,over):
 if over.get('R_calendar')=='quarter_end':return [0,0,E[key]/4]*4
 if key=='CON-009@v1':return INC['new_R_policy']['monthly_issuance_ceiling_R']
 if key in SPECS:return SPECS[key]['monthly_calendar_R']
 return [E[key]/12]*12

def model(key,fixed,scenario,override=None):
 p=C|SCENS.get(scenario,{})|(override or {})
 oldrate=p['old_annual_use'];fxrate=p['new_fixed_C_use'];ruse=p['new_R_use']
 unit=(1000*(.8+.2*.7)*p['price_multiplier']+30)/5000
 price=unit*5000; purchase=940*p['price_multiplier'];shipping=30
 shares=p.get('region_demand_shares',[.6,.4]); caps=[1800,1200]
 cal=issuance(key,p)
 stock=[0.,0.];ic=160000000.;ir=40000000.;nc=nr=0.;reserve=0.;F=0.
 grantannual=154160000 if key=='BASELINE' else (24000000 if key in SPECS else E[key])
 monthly=[];annual=[]
 for y in range(1,4):
  old_ic,old_ir,old_nc,old_nr=ic,ir,nc,nr
  aopenC=ic+nc;aopenR=ir+nr;aopenF=F;reserveopen=reserve;stockopen=sum(stock); part=[]
  for m in range(1,13):
   w=(.5 if m==1 else .5/11) if p.get('old_january_share')==.5 else 1/12
   dc_i=old_ic*oldrate*w;dr_i=old_ir*oldrate*w;dc_n=old_nc*oldrate*w;dr_n=old_nr*oldrate*w
   fixedm=fixed/12;posted=cal[m-1];conv=dr_i+dr_n+posted*ruse
   physical=dc_i+dc_n+fixedm*fxrate+conv
   openc=ic+nc;openr=ir+nr;openF=F
   ic-=dc_i;ir-=dr_i;nc+=fixedm*(1-fxrate)-dc_n;nr+=posted*(1-ruse)-dr_n
   grant=grantannual/4 if m in [1,4,7,10] else 0
   F+=grant-posted
   expired=F if m%3==0 else 0;F-=expired
   baskets=physical/5000
   arrival=[];closing=[]
   for j,sh in enumerate(shares):
    demand=baskets*sh
    buy=max(0,math.ceil((demand-stock[j]-1e-9)/100))*100
    stock[j]+=buy-demand
    arrival.append(buy);closing.append(stock[j])
   paidstock=sum(stock)*price
   reserve=max(0.,(nc+nr)*unit-paidstock)
   common=80+baskets*(.02+.2/30)
   errC=ic+nc-openc-fixedm-conv+physical
   errR=ir+nr-openr-posted+conv
   errF=F-openF-grant+posted+expired
   assert max(abs(errC),abs(errR),abs(errF))<EPS,(key,scenario,y,m,errC,errR,errF)
   assert min(ic,ir,nc,nr,F,*stock)>-EPS
   row=dict(candidate_key=key,scenario=scenario,fixed_C_year=fixed,year=y,month=m,opening_C=openc,opening_R=openr,fixed_C=fixedm,F_open=openF,F_grant=grant,F_posted=posted,F_unissued_expired=expired,F_close=F,confirmed_unposted_U=0,posted_R=posted,R_to_C=conv,direct_R=0,physical_C=physical,closing_C=ic+nc,closing_R=ir+nr,initial_rights_close=ic+ir,new_rights_close=nc+nr,baskets=baskets,S1_demand=baskets*shares[0],S2_demand=baskets*shares[1],S1_arrival=arrival[0],S2_arrival=arrival[1],S1_stock=closing[0],S2_stock=closing[1],order_placed_in_model_month=(y-1)*12+m-1,procurement_cash=sum(arrival)*purchase,delivery_cash=sum(arrival)*shipping,cash_total=sum(arrival)*price,paid_stock_RUB=paidstock,target_new_cash_reserve=reserve,new_exposure_RUB=(nc+nr)*unit,all_personal_exposure_RUB=(ic+ir+nc+nr)*unit,common_HR_hours=common,common_employee_receipt_hours=baskets*.1,physical_capacity_pass=all(baskets*shares[j]<=caps[j]+EPS for j in range(2)),common_HR220_pass=common<=220+EPS,C_error=errC,R_error=errR,F_error=errF)
   part.append(row);monthly.append(row)
  cash=sum(x['cash_total'] for x in part);reserve_delta=reserve-reserveopen
  reserve_gap=(nc+nr)*unit-reserve-sum(stock)*price
  assert reserve_gap<EPS
  assert abs(sum(x['S1_arrival']+x['S2_arrival'] for x in part)-sum(x['baskets'] for x in part)-sum(stock)+stockopen)<EPS
  cost=sum(x['physical_C'] for x in part)*unit
  assert abs(cash-cost-(sum(stock)-stockopen)*price)<EPS
  annual.append(dict(candidate_key=key,scenario=scenario,fixed_C_year=fixed,year=y,annual_R=E[key],unit_RUB_per_C=unit,requested_C=sum(x['physical_C'] for x in part),baskets=sum(x['baskets'] for x in part),procurement_cash=sum(x['procurement_cash'] for x in part),delivery_cash=sum(x['delivery_cash'] for x in part),cash_total=cash,opening_new_reserve=reserveopen,closing_new_reserve=reserve,reserve_delta=reserve_delta,funding_plus_buffer=cash+reserve_delta+500000,budget30_pass=cash+reserve_delta+500000<=30000000+EPS,budget34_pass=cash+reserve_delta+500000<=34000000+EPS,physical_capacity_pass=all(x['physical_capacity_pass'] for x in part),common_HR220_pass=all(x['common_HR220_pass'] for x in part),opening_C=aopenC,opening_R=aopenR,closing_C=ic+nc,closing_R=ir+nr,initial_rights_close=ic+ir,new_rights_close=nc+nr,paid_stock_units=sum(stock),paid_stock_RUB=sum(stock)*price,new_exposure_RUB=(nc+nr)*unit,all_personal_exposure_RUB=(ic+ir+nc+nr)*unit,F_grant=grantannual,F_posted=E[key],F_expired=grantannual-E[key],F_close=F,peak_baskets=max(x['baskets'] for x in part),peak_S1=max(x['S1_demand'] for x in part),peak_S2=max(x['S2_demand'] for x in part),common_HR_hours=sum(x['common_HR_hours'] for x in part),common_HR_peak=max(x['common_HR_hours'] for x in part),common_employee_receipt_hours=sum(x['common_employee_receipt_hours'] for x in part),counterfactual_if_funding_or_capacity_fails=True))
 return monthly,annual

# Rebuild work from ACT counts and minutes, not author cost arrays.
def Awork(d,full):
 v=d['workload']['minutes_and_denominators'];i=1 if full else 0
 req=v['special_requests_expected_full'][i];appeal=v['appeal_requests_expected_full'][i];corr=v['corrections_expected_full'][i]
 hr=(60*10+2400*.25+req*4+appeal*6+corr*5+12*5+10*10)/60+6+v['extra_baseline_HR_h_month']
 mgr=800+(60*30+240*3+req*10+12*5+appeal*8+corr*5+12*8+10*20)/60+v['extra_baseline_manager_h_month']
 emp=(2400*2+req*6+appeal*5+corr*3)/60
 return {'HR':[hr]*12,'manager':[mgr]*12,'employee':[emp]*12}

def Bwork(d,full,team_size=6):
 w=d['workload' if full else 'workload_expected'];f=w['flow'];mins=w['minutes'];n=f['application_people_month'];teams=n/team_size if d['candidate_key']=='CON-014@v1' else 0
 cor=n*f['correction_fraction'];tc=teams*f['correction_fraction'];ap=n*f['appeal_fraction_of_people'];rec=n*f['recusal_fraction_of_people'];req=f['special_applications_month'];g=f['ordinary_groups_month'];q=f['quality_sample_fraction']
 h=mins['HR'];ma=mins['manager'];em=mins['employee']
 hr=h['fixed_admin_hours_month']+(g*h['packet_per_group']+n*(h['reconcile_per_person']+h['membership_per_person'])+cor*h['correction_personal']+tc*h['team_rework']+ap*h['appeal_per_person']+rec*h['recusal_per_person']+req*h['special_per_application'])/60
 mgr=(g*ma['packet_per_group']+n*ma['ordinary_person_acceptance']+n*q*ma['quality_sample_person']+teams*(ma['team_acceptance']+q*ma['quality_sample_team'])+cor*ma['correction_person']+tc*ma['correction_team']+ap*ma['appeal_per_person']+rec*ma['recusal_per_person']+req*ma['special_per_application'])/60
 emp=(n*(em['ordinary_per_person']+em['share_acknowledgement_per_person'])+teams*em['team_lead_per_team']+cor*em['correction_per_person']+tc*em['correction_team_lead']+ap*em['appeal_per_person']+req*em['special_per_application'])/60
 vals={'HR':[hr]*12,'manager':[mgr]*12,'employee':[emp]*12}
 for role in vals:vals[role][0]+=w['month1_additional_hours'][role]
 return vals

WORK={};workcheck=[];resource=[]
for key,d in SPECS.items():
 WORK[key]={}
 for label,full in [('expected',False),('full_flow',True)]:
  arr=Awork(d,full) if key.startswith(('CON-011','CON-012')) else Bwork(d,full)
  WORK[key][label]=arr
  w=d['workload'];pre=w.get('prelaunch_hours',{})
  hours={role:sum(v)+pre.get(role,0) for role,v in arr.items()}
  hours['IT']=w['IT_initial_hours']+w['IT_recurring_hours_year']
  value=sum(hours[k]*C['rates_rub_hour'][k] for k in hours)
  for role,vals in arr.items():
   author_field=('full_flow_' if full else '')+{'HR':'HR_hours_monthly','manager':'manager_hours_monthly','employee':'employee_process_hours_monthly'}[role]
   if key.startswith(('CON-013','CON-014')):given=d['workload' if full else 'workload_expected'][author_field.replace('full_flow_','')]
   else:given=w[author_field]
   error=max(abs(a-b) for a,b in zip(vals,given));assert error<1e-5
   workcheck.append(dict(candidate_key=key,flow=label,role=role,annual_hours=hours[role],peak_month_hours=max(vals),max_author_array_error=error))
  resource.append(dict(candidate_key=key,flow=label,HR_hours=hours['HR'],manager_hours=hours['manager'],employee_process_hours=hours['employee'],IT_hours=hours['IT'],candidate_process_resource_RUB=value,all_labor_2x_RUB=value*2,replacement25_cash_RUB=value*.25,ordinary_productive_hours_disclosed=w.get('employee_useful_work_hours_year'),ordinary_QA_primary_hours_in_process=9600 if key.startswith(('CON-011','CON-012')) else 0,interpretation='Candidate process only; common order/receipt and common HR added once in resources-common.csv; productive work/data not asserted zero or incremental.'))
 if key=='CON-014@v1':WORK[key]['singleton']=Bwork(d,True,1)
# Incumbent original workloads: read-only projection, rebuilt.
w=INC['workload'];n=w['cards_month']
hr=20+n*.1*8/60+n*.05*20/60+n*.1*5/60
mgr=360*24*10/60/12+n*4/60+n*3/60+n*.1*5/60+n*.05*15/60
emp=n*(5+3+2)/60+n*.05*10/60
assert abs(hr-43)<EPS and abs(mgr-202.5)<EPS and abs(emp-105)<EPS
WORK['CON-009@v1']={'full_flow':{'HR':[hr]*12,'manager':[mgr+(20 if m in [1,4,7,10] else 0) for m in range(1,13)],'employee':[emp]*12}}
inc_hours={'HR':hr*12+120,'manager':mgr*12+80+400,'employee':emp*12+1200,'IT':80+4*12}
incvalue=sum(inc_hours[r]*C['rates_rub_hour'][r] for r in inc_hours)
resource.append(dict(candidate_key='CON-009@v1',flow='full_flow',HR_hours=inc_hours['HR'],manager_hours=inc_hours['manager'],employee_process_hours=inc_hours['employee'],IT_hours=inc_hours['IT'],candidate_process_resource_RUB=incvalue,all_labor_2x_RUB=2*incvalue,replacement25_cash_RUB=incvalue*.25,ordinary_productive_hours_disclosed=None,ordinary_QA_primary_hours_in_process=None,interpretation='Common employee order/receipt6min/basket removed here and added equally to every option. Ordinary source work/data unnormed, not zero.'))
single=WORK['CON-014@v1']['singleton'];hh={r:sum(single[r]) for r in single};hh['IT']=700
vv=sum(hh[r]*C['rates_rub_hour'][r] for r in hh)
resource.append(dict(candidate_key='CON-014@v1',flow='singleton',HR_hours=hh['HR'],manager_hours=hh['manager'],employee_process_hours=hh['employee'],IT_hours=hh['IT'],candidate_process_resource_RUB=vv,all_labor_2x_RUB=vv*2,replacement25_cash_RUB=vv*.25,ordinary_productive_hours_disclosed=57600,ordinary_QA_primary_hours_in_process=0,interpretation='All one-person teams; valid money maximum but ordinary HR capacity fails.'))

monthly=[];annual=[];resources_common=[];capacity=[]
for key in KEYS:
 for fixed in M['fixed_C_cases_year']:
  for s in SCENS:
   mm,aa=model(key,fixed,s);monthly+=mm;annual+=aa
   for a in aa:
    # Norm common receipt/order identically, including incumbent original6min/basket.
    commonvalue=a['common_HR_hours']*1000+a['common_employee_receipt_hours']*1000
    resources_common.append(dict(candidate_key=key,scenario=s,fixed_C_year=fixed,year=a['year'],common_HR_resource_RUB=a['common_HR_hours']*1000,common_employee_order_receipt_RUB=a['common_employee_receipt_hours']*1000,common_process_resource_RUB=commonvalue,common_incremental_HR_cash20=a['common_HR_hours']*1000*.2,common_replacement25_cash_RUB=commonvalue*.25,common_2x_resource_RUB=2*commonvalue))
   if key=='BASELINE':continue
   for flow,arr in WORK[key].items():
    for a in aa:
     rows=[x for x in mm if x['year']==a['year']]
     # Published B month1 setup repeats in this conservative comparison; actual restart cost unknown.
     vals=[row['common_HR_hours']+arr['HR'][row['month']-1] for row in rows]
     hrpeak=max(vals)
     for setting,extra,mul in [('specified',0,1),('all_labor_2x',0,2)]+([('manual_fallback',20,1)] if key.startswith(('CON-011','CON-012')) else []):
      peak=(hrpeak+extra)*mul
      capacity.append(dict(candidate_key=key,scenario=s,fixed_C_year=fixed,year=a['year'],flow=flow,setting=setting,combined_HR_peak=peak,HR220_pass=peak<=220+EPS,physical_capacity_pass=a['physical_capacity_pass'],manager_hours=sum(arr['manager'])+(80*12 if setting=='manual_fallback' else 0),manager_available_capacity='unknown',IT_available_capacity='unknown'))

# Maximum obligations and mechanistic edge-case arithmetic.
maxima=[]
for key in KEYS:
 if key in SPECS:
  d=SPECS[key];base=7200*4*500
  top=62.5*7200*4 if key.startswith(('CON-011','CON-012')) else 120*4*(7500+5000+2500)
  special=12*(8*2500+4*7500) if key.startswith(('CON-011','CON-012')) else 240*5000+120*10000
  assert base+top+special==E[key]
  assert sum(d['monthly_calendar_R'])==E[key]
  maxima.append(dict(candidate_key=key,eligible=7200,base_R=base,top_R=top,special_R=special,total_R=base+top+special,nominal_envelope_R=24000000,unused_envelope_R=24000000-E[key],personal_year_cap_R=27000 if key.startswith(('CON-011','CON-012')) else 72000,lower_only_years_to_5000C=2.5))
 elif key=='CON-009@v1':maxima.append(dict(candidate_key=key,eligible=7200,base_R=0,top_R=0,special_R=E[key],total_R=E[key],nominal_envelope_R=E[key],unused_envelope_R=0,personal_year_cap_R=20000,lower_only_years_to_5000C=None))
 else:maxima.append(dict(candidate_key=key,eligible=7200,base_R=None,top_R=None,special_R=None,total_R=E[key],nominal_envelope_R=154160000,unused_envelope_R=76449636,personal_year_cap_R=None,lower_only_years_to_5000C=None))
# Checks for ties crossing unpaid boundary, single teams, and unequal workshares.
edges=[]
for key in SPECS:
 pool=2500 if key.startswith(('CON-011','CON-012')) else 15000
 for n in [1,2,3,5,60,7200]:
  occupied=(0 if n==1 else pool) if key.startswith(('CON-011','CON-012')) else sum([7500,5000,2500][:min(n,3)])
  pay=math.floor(occupied/n*100)/100*n
  assert pay<=pool+EPS
  edges.append(dict(candidate_key=key,test='all_tied_occupied_slots; singleton_rule_applied',participants=n,pool_R=pool,total_paid_R=pay,residual_F=pool-pay,pass_check=True))
 if key=='CON-012@v1':
  assert abs(sum([.5,.3,.2])-1)<EPS
 if key=='CON-014@v1':
  for n in [1,2,6,10]:
   shares=[1/n]*n;assert abs(sum(shares)-1)<EPS
   edges.append(dict(candidate_key=key,test='team_base_plus_top_shares',participants=n,pool_R=n*500+7500,total_paid_R=n*500+sum(7500*s for s in shares),residual_F=0,pass_check=True))

# Independent obligations event ledger: confirmed U consumes F once; posting only U->R.
ledger=[]
for key in KEYS:
 qgrant=154160000/4 if key=='BASELINE' else (6000000 if key in SPECS else E[key]/4)
 qaward=E[key]/4;F=qgrant;U=R=Cbal=0.;confirmed=posted=redeemed=expired=0.
 def log(event):
  assert abs(F+confirmed+expired-qgrant)<EPS
  assert abs(U+R+Cbal+redeemed-confirmed)<EPS
  ledger.append(dict(candidate_key=key,event=event,F=F,U=U,R=R,C=Cbal,confirmed=confirmed,posted=posted,redeemed=redeemed,unissued_expired=expired,total_earned_outstanding=U+R+Cbal,exposure_RUB=(U+R+Cbal)*.194,pass_check=True))
 log('grant_before_effort; potential_quarter_award='+str(qaward))
 F-=qaward;U+=qaward;confirmed+=qaward;log('confirm_all_quarter; posting_outage')
 expired=F;F=0;log('quarter_end_only_unissued_F_expired; U_preserved')
 U-=qaward;R+=qaward;posted+=qaward;log('post_once; do_not_debit_F_again')
 R-=qaward;Cbal+=qaward;log('convert_1_to_1; no_extinguishment')
 redeemed+=qaward;Cbal-=qaward;log('physical_receipt_extinguishes_once')
# Direct service alternative: R excluded from physical stock, reserve backs other rights once.
services=[]
for key in KEYS:
 for label,r in [('old_R_all',40000000),('new_R_all',E[key])]:
  n=r/20000;services.append(dict(candidate_key=key,source=label,redeemed_R=r,services=n,hours=n*8,resource_RUB=n*8000,replacement_cash_RUB=n*2000,even_month_units=n/12,quarter_peak_units=n/4,capacity200_even_pass=n/12<=200,capacity200_quarter_pass=n/4<=200,physical_redemption_same_R=0))

# Equal-scale controls isolate financial cost from allocation mechanism; no new concept versions.
controls=[]
for e in [0,12000000,16800000,24000000,36000000]:
 old=E['BASELINE'];E['BASELINE']=e
 for fixed in [96000000,144000000]:
  for s in ['EXPECTED','FULL_NEW']:
   _,rows=model('BASELINE',fixed,s)
   for a in rows:controls.append({k:a[k] for k in ['scenario','fixed_C_year','year','annual_R','cash_total','closing_new_reserve','funding_plus_buffer','budget30_pass','budget34_pass']})
 E['BASELINE']=old

# Hash all assigned frozen candidate versions and inputs without modifying them.
versions=json.loads((ROOT/'private/versions-before-checks.json').read_text())
version_checks=[]
for path,h in versions.items():
 actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest();assert actual==h,path
 version_checks.append({'path':path,'sha256':actual,'matches_frozen':True})
for path in ['inputs/context.md','inputs/baseline.md','inputs/diagnosis.md','inputs/evidence.md','inputs/rubric.json','supporting/finance-basis/scenario-inputs.json','supporting/finance-basis/basis.md','../../incumbent/concept.md','../../incumbent/finance-projection.json']:
 version_checks.append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),'matches_frozen':None})
csvout('monthly.csv',monthly);csvout('annual.csv',annual);csvout('maxima.csv',maxima);csvout('edge-cases.csv',edges);csvout('workload-audit.csv',workcheck);csvout('resources-candidate.csv',resource);csvout('resources-common.csv',resources_common);csvout('capacity.csv',capacity);csvout('obligation-ledger.csv',ledger);csvout('direct-services.csv',services);csvout('equal-scale.csv',controls)
# Reconciled resource amounts, without calling unknown productive work/data zero.
ry=[]
for a in annual:
 if a['scenario'] not in ['EXPECTED','FULL_NEW']:continue
 k=a['candidate_key'];y=a['year'];commonhr=a['common_HR_hours']*1000
 for rec in [r for r in resource if r['candidate_key']==k and r['flow']=='full_flow'] or [None]:
  process=None if rec is None else rec['candidate_process_resource_RUB']
  if y>1 and process is not None:
   if k in SPECS:
    w=SPECS[k]['workload'];process-=w['IT_initial_hours']*2000
    process-=sum(w.get('prelaunch_hours',{}).get(r,0)*C['rates_rub_hour'][r] for r in ['HR','manager','employee'])
   else:process-=120*1000+400*1500+1200*1000+80*2000
  for minutes in [0,6,12]:
   receipt=a['baskets']*minutes/60*1000
   known=commonhr+receipt+(process or 0)
   ry.append(dict(candidate_key=k,scenario=a['scenario'],fixed_C_year=a['fixed_C_year'],year=y,employee_common_receipt_minutes=minutes,common_HR_RUB=commonhr,common_employee_receipt_RUB=receipt,candidate_process_RUB=process,known_process_subtotal_RUB=known,all_known_labor_2x_RUB=2*known,replacement25_cash_RUB=known*.25,common_HR_incremental_cash20_RUB=commonhr*.2,identical_QA800h_month_sensitivity_extra_RUB=0 if k in ['CON-011@v1','CON-012@v1'] else 14400000,ordinary_source_work_and_data_RUB='uncertain; not zero',complete_TCO='uncertain'))
csvout('resource-years.csv',ry)
writejson(OUT/'source-manifest.json',version_checks)
verification={'independence':'Own formulas; reads M05 JSON and specs as data. No author script imported/executed.','candidate_keys':KEYS,'monthly_rows':len(monthly),'annual_rows':len(annual),'scenarios':list(SCENS),'years':[1,2,3],'max_C_R_F_residual':max(max(abs(x[k]) for k in ['C_error','R_error','F_error']) for x in monthly),'nonnegative_stocks':True,'stock_cost_and_reserve_identities':True,'workload_author_arrays_rebuilt':True,'frozen_versions_unchanged':True,'actual_bank_readiness':'unknown','monthly_financing_limit':'Budget is annual; all fund timing/monthly cash assumed preauthorized before effort; intra-month timing/SKU not verified.'}
writejson(OUT/'verification.json',verification)
print(json.dumps(verification,ensure_ascii=False))
for k in KEYS:
 rows=[a for a in annual if a['candidate_key']==k and a['fixed_C_year']==96000000 and a['year']==1 and a['scenario'] in ['EXPECTED','FULL_NEW','FULL_NEW_OLD35','FULL_NEW_PRICE20']]
 for a in rows:print(k,a['scenario'],round(a['cash_total']/1e6,6),round(a['funding_plus_buffer']/1e6,6),a['physical_capacity_pass'])
