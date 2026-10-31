#!/usr/bin/env python3.12
"""Independent finance audit round002; monetary core COPIED from sealed001, then adapted in002 only. Reads specifications as DATA; imports no author/M05 code.
Run from any cwd: python3.12 <this file>. Outputs only assigned checks paths.
All money RUB; currency C/R; baskets are normalized divisible demand units.
"""
import csv, hashlib, json, math, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--source-snapshot');args=parser.parse_args()
SNAPSHOT=(ROOT/args.source_snapshot).resolve() if args.source_snapshot else None
def source(path):
 return SNAPSHOT/path if SNAPSHOT and str(path).startswith('branches/') else ROOT/path
M=json.loads((ROOT/'supporting/finance-basis/scenario-inputs.json').read_text())
C=M['common']; EPS=1e-6
SPECS={}
for rec in json.loads((ROOT/'candidate-inputs.json').read_text())['candidates']:
 SPECS[rec['candidate_key']]=json.loads(source(rec['spec']).read_text())
SPECS['CON-013@v1']=json.loads((ROOT/'supporting/previous-best/finance-spec.json').read_text())
KEYS=['BASELINE','CON-013@v1','CON-013@v2','CON-011@v2']
E={'BASELINE':19427591*4,**{k:s['annual_total_R'] for k,s in SPECS.items()}}
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

# Round002 resource model: independently rebuild every component from acts and minutes.
def work013():
 n=2400;metric=n*.6;artifact=n*.4;units=3;ready=.7;new=.3
 qa_metric=metric*42.5*.5/60;qa_artifact=artifact*units*12/60;qa=qa_metric+qa_artifact
 evidence_metric=metric*42.5*.25/60;evidence_artifact=artifact*units*20/60
 hr=12+(40*10+n*.25+n*.1*2+n*.02*5+n*.01*3+40*5)/60
 award_mgr=(40*10+n*ready*1+n*new*3+n*ready*.1*2+n*.1*5+n*.02*8+n*.01*5+40*12)/60
 submission=(n*3+n*.1*4+n*.02*4+40*6)/60
 mgr=qa+award_mgr;emp=submission+evidence_metric+evidence_artifact
 existing_manager=qa*ready;existing_employee=evidence_metric+evidence_artifact*ready
 resource=hr*1000+mgr*1500+emp*1000+10*2000
 incremental=hr*1000+(mgr-existing_manager)*1500+(emp-existing_employee)*1000+10*2000
 return dict(HR=hr,manager=mgr,employee=emp,submission=submission,evidence=evidence_metric+evidence_artifact,QA=qa,existing_manager=existing_manager,existing_employee=existing_employee,incremental_month_RUB=incremental,all_month_RUB=resource,useful_hours=metric*2+artifact*units*2,IT=10)
def work011():
 hr=6+(60*10+2400*.25+200*4+120*6+72*5+12*5+10*10)/60
 mgr=(60*30+240*3+200*10+48*5+120*8+72*5+12*8+10*20)/60
 emp=(2400*2+200*6+120*5+72*3)/60
 award=hr*1000+mgr*1500+emp*1000+12*2000
 return dict(HR=hr,manager=mgr+800,employee=emp,submission=emp,evidence=None,QA=800,award_manager=mgr,existing_manager=None,existing_employee=None,incremental_month_RUB=None,award_month_RUB=award,all_month_RUB=award+800*1500,useful_hours=None,IT=12)
def work_prior():
 n=2400;hr=12+(40*10+n*.25+n*.1*2+n*.02*5+n*.01*3+40*5)/60
 mgr=(40*10+n*4+n*.1*4+n*.1*5+n*.02*8+n*.01*5+40*12)/60
 emp=(n*3+n*.1*4+n*.02*4+40*6)/60
 return dict(HR=hr,manager=mgr,employee=emp,QA=None,existing_manager=None,existing_employee=None,all_month_RUB=hr*1000+mgr*1500+emp*1000+10*2000,IT=10)
WORK={'CON-013@v2':work013(),'CON-011@v2':work011(),'CON-013@v1':work_prior()}
work_audit=[]
for key,w in WORK.items():
 d=SPECS[key]['workload']
 for role,field in [('HR','HR_hours_monthly'),('manager','manager_hours_monthly'),('employee','employee_process_hours_monthly')]:
  norm=w[role]
  if key=='CON-011@v2' and role=='manager':norm-=800
  # Prior month1 includes one-off preparation and is separately shown.
  expected=d[field][1:] if key=='CON-013@v1' else d[field]
  assert max(abs(float(v)-norm) for v in expected)<1e-5,(key,role,norm,expected)
  work_audit.append(dict(candidate_key=key,component=role,independent_hours_month=norm,author_arrays_match=True))
if True:
 w=WORK['CON-013@v2'];assert abs(w['all_month_RUB']*12-38656800)<EPS
 assert abs(w['incremental_month_RUB']*12-13849200)<EPS
 w=WORK['CON-011@v2'];assert abs(w['award_month_RUB']*12-4284000)<EPS
 assert abs(w['all_month_RUB']*12-18684000)<EPS

monthly=[];annual=[];capacity=[];resource=[]
for key in KEYS:
 for fixed in M['fixed_C_cases_year']:
  for s in SCENS:
   mm,aa=model(key,fixed,s);monthly+=mm;annual+=aa
   if key=='BASELINE':continue
   w=WORK[key]
   for y in range(1,4):
    yy=[x for x in mm if x['year']==y]
    own=[w['HR']+(20 if key=='CON-013@v1' and x['month']==1 else 0) for x in yy]
    for setting,extra,mul in [('specified',0,1),('all_labor_2x',0,2)]+([('manual_export',20,1),('source_creation',20,1)] if key=='CON-011@v2' else []):
     peak=max((x['common_HR_hours']+h+extra)*mul for x,h in zip(yy,own))
     capacity.append(dict(candidate_key=key,scenario=s,fixed_C_year=fixed,year=y,setting=setting,HR_peak=peak,HR220_pass=peak<=220+EPS,physical_capacity_pass=all(x['physical_capacity_pass'] for x in yy),manager_employee_IT_available='uncertain'))
    if s in ['EXPECTED','FULL_NEW']:
     a=next(x for x in aa if x['year']==y)
     commonHR=a['common_HR_hours']*1000;receipt=a['baskets']*.1*1000
     process=w['all_month_RUB']*12
     startup=0
     if key=='CON-013@v1':process+=20*1000+30*1500+720*1000 # conservative recurring author month1 arrays
     if y==1:
      if key=='CON-013@v2':startup=50*1000+480*1500+720*1000+400*2000
      elif key=='CON-011@v2':startup=54*1000+180*1500+1800*1000+520*2000
      else:startup=400*2000
     resource.append(dict(candidate_key=key,scenario=s,fixed_C_year=fixed,year=y,own_full_valued_process_RUB=process,existing_business_RUB=w['existing_manager']*1500*12+w['existing_employee']*1000*12 if w['existing_manager'] is not None else None,incremental_program_RUB=w.get('incremental_month_RUB')*12 if w.get('incremental_month_RUB') is not None else None,award_only_RUB=w.get('award_month_RUB',0)*12 if 'award_month_RUB'in w else None,startup_RUB=startup,common_HR_RUB=commonHR,common_employee_receipt6min_RUB=receipt,known_resource_subtotal_RUB=process+startup+commonHR+receipt,known_subtotal_2x_RUB=2*(process+startup+commonHR+receipt),replacement25_cash_on_known_RUB=.25*(process+startup+commonHR+receipt),common_HR_cash20_RUB=.2*commonHR,QA_existing_incrementality='assumed70/30' if key=='CON-013@v2' else 'uncertain',ordinary_useful_hours_year=w.get('useful_hours')*12 if w.get('useful_hours') else None,complete_actual_TCO='uncertain'))

# Prospective launch. Request escrow remains in C until actual receipt.
# Forecast batches use a book stock before capacity constraints; actual stock includes queue backing.
LAUNCHSCENS={k:v for k,v in SCENS.items() if k not in ['QUARTER_END_R','FULL_NEW_QUARTER_END_R']}
LAUNCHSCENS.update({'DELAYED_POST':{},'EMPTY_SHOP':{}})
NEW=['CON-013@v2','CON-011@v2']

def launch_work(key,t):
 w=WORK[key];closed=t>=4
 if key=='CON-013@v2':
  prepHR=[30,10,10][t-1] if t<=3 else 0;prepM=160 if t<=3 else 0;prepE=240 if t<=3 else 0
  hr=w['HR'] if closed else 12+40*5/60
  mgr=w['manager'] if closed else 40*12/60
  submission=w['submission'] if closed else 40*6/60
  evidence=w['evidence'];qa=w['QA'] if closed else 0
  it=( [200,100,100][t-1] if t<=3 else 0)+10
  existingM=w['existing_manager'] if closed else 0;existingE=w['existing_employee']
  useful=w['useful_hours']*min(t/3,1)
  total=dict(HR=hr+prepHR,manager=mgr+prepM,submission=submission+prepE,evidence=evidence,employee=submission+prepE+evidence,IT=it,QA=qa,existing_manager=existingM,existing_employee=existingE,useful=useful)
 else:
  prepHR=[38,8,8][t-1] if t<=3 else 0;prepM=[120,30,30][t-1] if t<=3 else 0;prepE=600 if t<=3 else 0
  hr=w['HR'] if closed else 6+(200*4+12*5+10*10)/60
  mgr=w['award_manager'] if closed else (200*10+48*5+12*8+10*20)/60
  emp=w['employee'] if closed else 200*6/60
  qa=800 if closed else 0
  total=dict(HR=hr+prepHR,manager=mgr+prepM+qa,award_manager=mgr+prepM,submission=emp+prepE,evidence=None,employee=emp+prepE,IT=([120,200,200][t-1] if t<=3 else 0)+12,QA=qa,existing_manager=None,existing_employee=None,useful=None)
 total['all_process_RUB']=total['HR']*1000+total['manager']*1500+total['employee']*1000+total['IT']*2000
 total['existing_RUB']=None if total['existing_manager'] is None else total['existing_manager']*1500+total['existing_employee']*1000
 total['incremental_RUB']=None if total['existing_RUB'] is None else total['all_process_RUB']-total['existing_RUB']
 return total

def launch(key,fixed,scenario,months=36,stop_new_after=None,parameter_overrides=None):
 p=C|LAUNCHSCENS[scenario]|(parameter_overrides or {});rate=p['old_annual_use'];fx=p['new_fixed_C_use'];rr=p['new_R_use'];unit=(940*p['price_multiplier']+30)/5000;price=unit*5000
 shares=p.get('region_demand_shares',[.6,.4]);stock=[0.,0.];book=[0.,0.];queue=[0.,0.];ic=160e6;ir=40e6;nc=nr=0.;U=0.;conditional=0.;Rsv=0.
 out=[]
 for t in range(1,months+1):
  year=(t-1)//12+1;m=(t-1)%12+1
  if m==1:old_ic,old_ir,old_nc,old_nr=ic,ir,nc,nr
  w=(.5 if m==1 else .5/11) if p.get('old_january_share') else 1/12
  newpromise=1800000 if stop_new_after is None or t<=stop_new_after else 0
  mature=1800000 if t>=4 and (stop_new_after is None or t-3<=stop_new_after) else 0
  special=200000 if stop_new_after is None or t<=stop_new_after else 0
  conditional_open=conditional;conditional+=newpromise-mature
  confirmed=mature+special;openingU=U
  if scenario=='DELAYED_POST' and t==4:posted=confirmed-180000
  else:posted=confirmed+U
  U+=confirmed-posted
  openC=ic+nc+sum(queue)*5000;openR=ir+nr
  dc_i=old_ic*rate*w;dr_i=old_ir*rate*w;dc_n=old_nc*rate*w;dr_n=old_nr*rate*w
  ic-=dc_i;ir-=dr_i;nc+=fixed/12*(1-fx)-dc_n;nr+=posted*(1-rr)-dr_n
  conv=dr_i+dr_n+posted*rr;requested=dc_i+dc_n+fixed/12*fx+conv
  want=[requested/5000*sh for sh in shares];arrivals=[];received=[]
  for j in range(2):
   # A surprise posting outage after preordering cannot retroactively shrink this month's arrival.
   forecast_extra=(180000*rr/5000*shares[j]) if scenario=='DELAYED_POST' and t==4 else 0
   buy=max(0,math.ceil((want[j]+forecast_extra-book[j]-1e-9)/100))*100
   if scenario=='EMPTY_SHOP' and t==1:buy=0
   arrivals.append(buy);book[j]+=buy-want[j];stock[j]+=buy;queue[j]+=want[j]
   deliver=min(queue[j],stock[j],C['regions'][j]['capacity_units_month'])
   stock[j]-=deliver;queue[j]-=deliver;received.append(deliver)
  actualC=sum(received)*5000;queueC=sum(queue)*5000;closeC=ic+nc+queueC;closeR=ir+nr
  paid=sum(stock)*price;new_exp=(nc+nr+U+queueC)*unit
  earned_res=max(0.,new_exp-paid)
  total=max(0.,new_exp+conditional*unit-paid);conditional_extra=total-earned_res
  cash=sum(arrivals)*price;delta=total-Rsv;Rsv=total
  errC=closeC-openC-fixed/12-conv+actualC;errR=closeR-openR-posted+conv
  assert max(abs(errC),abs(errR))<EPS,(key,t,errC,errR)
  assert abs(conditional+sum(x['confirmed_R']-x['special_R'] for x in out)+mature-sum(x['new_conditional_R'] for x in out)-newpromise)<EPS
  assert min(ic,ir,nc,nr,U,conditional,*stock,*queue)>-EPS
  assert abs(sum(stock)-sum(book)-sum(queue))<EPS
  assert total+paid+EPS>=new_exp+conditional*unit
  work=launch_work(key,t)
  common=80+requested/5000*(.02+.2/30)
  # Extra same6min per basket on the same lifecycle basis for every option.
  employee_common=requested/5000*.1
  row=dict(candidate_key=key,scenario=scenario,fixed_C_year=fixed,year=year,month=t,month_in_year=m,new_conditional_R=newpromise,matured_conditional_R=mature,conditional_open_R=conditional_open,conditional_close_R=conditional,special_R=special,confirmed_R=confirmed,U_open_R=openingU,U_peak_R=openingU+confirmed,posted_R=posted,U_close_R=U,committed_authorization_F_close=conditional+U,opening_C=openC,opening_R=openR,fixed_C=fixed/12,R_to_C=conv,requested_C=requested,received_C=actualC,orders_pending_C=queueC,closing_C=closeC,closing_R=closeR,unrequested_new_C=nc,unrequested_new_R=nr,old_unrequested_C_R=ic+ir,S1_new_orders=want[0],S2_new_orders=want[1],S1_received=received[0],S2_received=received[1],S1_queue=queue[0],S2_queue=queue[1],S1_paid_stock=stock[0],S2_paid_stock=stock[1],S1_arrival=arrivals[0],S2_arrival=arrivals[1],paid_stock_RUB=paid,procurement_cash=sum(arrivals)*940*p['price_multiplier'],delivery_cash=sum(arrivals)*30,cash_total=cash,new_and_requested_exposure_RUB=new_exp,earned_reserve_RUB=earned_res,conditional_prefunding_RUB=conditional_extra,total_reserve_RUB=total,reserve_delta_RUB=delta,funding_without_buffer=cash+delta,common_HR_hours=common,own_HR_hours=work['HR'],total_HR_hours=common+work['HR'],HR220_pass=common+work['HR']<=220+EPS,employee_common_receipt_hours=employee_common,manager_including_QA_hours=work['manager'],employee_submission_hours=work['submission'],employee_evidence_hours=work['evidence'],employee_total_process_hours=work['employee'],primary_QA_hours=work['QA'],IT_hours=work['IT'],existing_business_RUB=work['existing_RUB'],incremental_program_RUB=work['incremental_RUB'],own_all_process_RUB=work['all_process_RUB'],ordinary_useful_hours=work['useful'],no_queue=queueC<EPS,C_error=errC,R_error=errR)
  out.append(row)
 return out

launch_monthly=[];launch_annual=[];phases=[]
for key in NEW:
 for fixed in M['fixed_C_cases_year']:
  for s in LAUNCHSCENS:
   rows=launch(key,fixed,s);launch_monthly+=rows
   for y in range(1,4):
    yy=[r for r in rows if r['year']==y];end=yy[-1];begin=yy[0];cash=sum(r['cash_total'] for r in yy);fund=sum(r['funding_without_buffer'] for r in yy)
    launch_annual.append(dict(candidate_key=key,scenario=s,fixed_C_year=fixed,year=y,posted_R=sum(r['posted_R'] for r in yy),confirmed_R=sum(r['confirmed_R'] for r in yy),cash_total=cash,procurement_cash=sum(r['procurement_cash'] for r in yy),delivery_cash=sum(r['delivery_cash'] for r in yy),reserve_delta=fund-cash,total_reserve_close=end['total_reserve_RUB'],conditional_close_R=end['conditional_close_R'],U_close_R=end['U_close_R'],paid_stock_RUB=end['paid_stock_RUB'],orders_pending_C=end['orders_pending_C'],funding_plus_buffer=fund+500000,budget30_pass=fund+500000<=30e6+EPS,budget34_pass=fund+500000<=34e6+EPS,no_queue_all_months=all(r['no_queue'] for r in yy),HR220_pass=all(r['HR220_pass'] for r in yy),HR_peak=max(r['total_HR_hours'] for r in yy),own_HR_hours=sum(r['own_HR_hours'] for r in yy),manager_including_QA_hours=sum(r['manager_including_QA_hours'] for r in yy),employee_submission_hours=sum(r['employee_submission_hours'] for r in yy),employee_evidence_hours=sum(r['employee_evidence_hours'] or 0 for r in yy) if key=='CON-013@v2' else None,QA_required_hours=sum(r['primary_QA_hours'] for r in yy),IT_hours=sum(r['IT_hours'] for r in yy),existing_business_RUB=sum(r['existing_business_RUB'] for r in yy) if key=='CON-013@v2' else None,incremental_program_RUB=sum(r['incremental_program_RUB'] for r in yy) if key=='CON-013@v2' else None,own_all_process_RUB=sum(r['own_all_process_RUB'] for r in yy),common_HR_RUB=sum(r['common_HR_hours'] for r in yy)*1000,common_employee_receipt_RUB=sum(r['employee_common_receipt_hours'] for r in yy)*1000,ordinary_useful_hours=sum(r['ordinary_useful_hours'] for r in yy) if key=='CON-013@v2' else None))
   if fixed==96000000 and s in ['EXPECTED','FULL_NEW']:
    fiscal_cash=0
    for row in rows:
     t=row['month'];mi=row['month_in_year'];fiscal_cash=0 if mi==1 else fiscal_cash;fiscal_cash+=row['cash_total']
     # Explicit feasible date schedule: this month's ordered goods arrive/are paid before14th;
     # old/fixed receipt occurs before14th; ordinary/special awaiting finalization are still inventory.
     # These are audit assumptions, not hidden claims that bank supply timing is known.
     unit=.194;pending_current=row['confirmed_R'];inventory_before=row['paid_stock_RUB']+pending_current*unit
     gross_cond_before=row['conditional_close_R']+row['matured_conditional_R']
     unearned_special=row['special_R']
     exposure_before=row['new_and_requested_exposure_RUB']+(gross_cond_before+unearned_special)*unit
     target_before=max(0.,exposure_before-inventory_before)
     assert abs(target_before-row['total_reserve_RUB'])<EPS
     opening_year_res=0 if row['year']==1 else next(z for z in rows if z['month']==(row['year']-1)*12)['total_reserve_RUB']
     phasefund=fiscal_cash+target_before-opening_year_res+500000
     phases.append(dict(candidate_key=key,scenario=s,year=row['year'],month=t,promise_date_day=14,effort_start_day=15,prior_quality_close_day=24 if key=='CON-013@v2' else 28,ordinary_conditional_peak_R=gross_cond_before,special_unconfirmed_max_R=unearned_special,earned_or_requested_exposure_RUB=row['new_and_requested_exposure_RUB'],paid_stock_before_late_posting_RUB=inventory_before,paid_stock_after_receipt_RUB=row['paid_stock_RUB'],net_reserve_before_effort_RUB=target_before,net_reserve_month_close_RUB=row['total_reserve_RUB'],fiscal_cash_so_far_RUB=fiscal_cash,opening_year_reserve_RUB=opening_year_res,fiscal_funding_including_buffer_RUB=phasefund,budget34_pass=phasefund<=34e6+EPS,conditional_peak_currency_preserved=True,date_condition='Forecast appropriate inventory must be received/paid and allocated once before14th; alternatively verified liquid cash backing. Actual timing unknown.'))
# A finite stop demonstrates that newly promised windows beyond m15/m36 are not erased.
tail=[]
for key in NEW:
 for cutoff in [15,36]:
  rows=launch(key,96000000,'FULL_NEW',cutoff+3,cutoff)
  for row in rows:
   if row['month']>=cutoff:tail.append({k:row[k] for k in ['candidate_key','month','new_conditional_R','matured_conditional_R','conditional_close_R','U_close_R','posted_R','orders_pending_C','cash_total','total_reserve_RUB']}|{'stop_new_promise_after_month':cutoff})
  assert rows[-1]['conditional_close_R']==0 and rows[-1]['U_close_R']==0
# Literal money formulas, adversarial ties/small groups and team shares.
from fractions import Fraction
edge=[]
def prizes(key,n):
 pool=Fraction(250*n)
 if key=='CON-011@v2':return [pool*Fraction(4,5),pool*Fraction(1,5)]
 one=Fraction(math.floor(pool*100/2),100);two=Fraction(math.floor(pool*100/3),100)
 return [one,two,pool-one-two]
def pay(key,n,groups,rank_ties=None,sole=False):
 slots=prizes(key,n);out=[];rank=0
 for tied in (rank_ties or [[i] for i in range(len(groups))]):
  payout=sum(slots[rank:rank+len(tied)],Fraction())/len(tied)
  if sole and key=='CON-011@v2':payout=0
  for team in tied:
   for weight in groups[team]:
    value=payout*weight
    unit=1 if key=='CON-011@v2' else 100
    out.append(Fraction(math.floor(value*unit),unit))
  rank+=len(tied)
 assert sum(out)<=250*n
 return out
for key in NEW:
 for n,k in [(40,8),(10,2),(60,60),(1,1)]:
  sizes=[5]*8 if (n,k)==(40,8) else [3,7] if n==10 else [1]*k
  groups=[[Fraction(1,size)]*size for size in sizes]
  for tied in [True,False]:
   arr=pay(key,n,groups,[list(range(k))] if tied else None,k==1)
   edge.append(dict(candidate_key=key,case=f'headcount{n}_units{k}_alltie{tied}',pool_R=250*n,paid_top_R=float(sum(arr)),per_person_first=float(arr[0]),residual_F_R=250*n-float(sum(arr)),pass_check=True))
# Explicit examples all include lower500 where the source does.
examples013={'40_people_8_tied_teams_5_each_person':750,'40_tied_persons':750,'40_people_team_rank1_each':1500,'40_people_team_rank2_each':float(Fraction(500)+Fraction(math.floor(Fraction(10000,3)/5*100),100)),'40_people_team_rank3_each':833.33,'8_separate_groups_of5_sole_eligible_team_each_person':625,'small_group5_one_top_person':1125,'singleton_L2':625,'60_group_rank2_through6_tie5':2000,'60_group_third_tied3':1333.33,'rolling4cycles_person_max':4*500+4*7500+4*10000}
for x in csv.DictReader(source('branches/A/money-examples.csv').open()):assert abs(float(x['computed_R'])-examples013[x['case']])<.001
assert float(pay('CON-011@v2',40,[[Fraction(1,5)]*5 for _ in range(8)])[0])==1600
assert sum(pay('CON-011@v2',40,[[Fraction(1)] for _ in range(3)],[[0,1,2]]))==9999
assert 7200*4*500+7200*4*250+12*200000==24000000
assert 4*500+4*20000+2*7500==97000

# Compare every published launch row with independently calculated states, not author functions.
compare=[]
for key,path in [('CON-013@v2','branches/A/first-launch.csv'),('CON-011@v2','branches/B/first-launch.csv')]:
 for given in csv.DictReader(source(path).open()):
  s=given['scenario'];s='EMPTY_SHOP' if s=='COLD_SHOP_STRESS' else s
  fx=int(given.get('fixed_C_year',96000000));t=int(given['month'])
  if key=='CON-011@v2' and given['scenario']=='COLD_SHOP_STRESS':
   # Published cold-shop uses full fixed; common EMPTY_SHOP grid uses expected fixed.
   own=launch(key,fx,'EMPTY_SHOP',15,parameter_overrides={'new_fixed_C_use':1.})[t-1]
  else:own=next(x for x in launch_monthly if x['candidate_key']==key and x['scenario']==s and x['fixed_C_year']==fx and x['month']==t)
  mapping={'posted_R':'posted_R','confirmed_R':'confirmed_R','U_close_R':'U_close_R','R_to_C':'R_to_C','requested_C':'requested_C'}
  if key=='CON-013@v2':mapping.update({'received_C':'received_C','orders_pending_C_close':'orders_pending_C','cash_RUB':'cash_total','reserve_close_RUB':'earned_reserve_RUB','conditional_prefunding_RUB':'conditional_prefunding_RUB','conditional_close_R':'conditional_close_R','paid_inventory_close_RUB':'paid_stock_RUB','total_HR_hours':'total_HR_hours','manager_hours_including_primary_QA':'manager_including_QA_hours','employee_process_hours':'employee_submission_hours','employee_evidence_hours':'employee_evidence_hours','existing_business_resource_RUB':'existing_business_RUB','required_incremental_program_resource_RUB':'incremental_program_RUB'})
  else:mapping.update({'received_and_redeemed_C':'received_C','unfulfilled_orders_C_close':'orders_pending_C','procurement_including_logistics_cash_RUB':'cash_total','total_reserve_RUB_close':'total_reserve_RUB','conditional_unearned_close_R':'conditional_close_R','inventory_value_RUB':'paid_stock_RUB','combined_HR_hours':'total_HR_hours','manager_quality_plus_award_required_hours':'manager_including_QA_hours','employee_total_hours':'employee_total_process_hours'})
  for authorfield,ourfield in mapping.items():
   err=float(given[authorfield])-float(own[ourfield])
   compare.append(dict(candidate_key=key,source_path=path,scenario=s,fixed_C_year=fx,month=t,field=authorfield,independent_value=own[ourfield],author_value=float(given[authorfield]),error=err,match=abs(err)<1e-5))
# Annual source claims: compare full year2, not the partial m13..15 table.
annual_compare=[]
for x in csv.DictReader(source('branches/A/launch-years.csv').open()):
 y=next(y for y in launch_annual if y['candidate_key']=='CON-013@v2' and y['scenario']==x['scenario'] and y['fixed_C_year']==int(x['fixed_C_year']) and y['year']==int(x['year']))
 for field,ours in [('cash_RUB','cash_total'),('funding_plus_buffer_RUB','funding_plus_buffer'),('orders_pending_C_close','orders_pending_C'),('existing_business_resource_RUB','existing_business_RUB'),('required_incremental_program_resource_RUB','incremental_program_RUB')]:
  err=float(x[field])-y[ours];annual_compare.append(dict(candidate_key='CON-013@v2',scenario=x['scenario'],fixed_C_year=x['fixed_C_year'],year=x['year'],field=field,error=err,match=abs(err)<1e-5))

# Equal monetary envelope controls isolate policy scale from mechanism.
controls=[]
for e in [0,12000000,24000000,36000000]:
 old=E['BASELINE'];E['BASELINE']=e
 for fx in [96000000,144000000]:
  for s in ['EXPECTED','FULL_NEW']:
   _,aa=model('BASELINE',fx,s)
   for x in aa:controls.append({k:x[k] for k in ['scenario','fixed_C_year','year','annual_R','cash_total','closing_new_reserve','funding_plus_buffer','budget30_pass','budget34_pass']})
 E['BASELINE']=old
manifest=[]
for path,h in json.loads((ROOT/'private/versions-before-checks.json').read_text()).items():
 actual=hashlib.sha256(source(path).read_bytes()).hexdigest();assert actual==h,path
 manifest.append(dict(path=path,sha256=actual,frozen_match=True))
for path in ['../001/checks/finance/model.py','../001/checks/finance/verify.py','../001/selected.md','supporting/previous-best/finance-spec.json','supporting/previous-best/concept.md','supporting/finance-basis/scenario-inputs.json','supporting/finance-basis/basis.md','clarifications.md',*['inputs/'+n for n in ['context.md','baseline.md','evidence.md','diagnosis.md','rubric.json']]]:
 manifest.append(dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),frozen_match=None))
for name,data in [('monthly.csv',monthly),('annual.csv',annual),('capacity.csv',capacity),('resources.csv',resource),('workload-audit.csv',work_audit),('launch-monthly.csv',launch_monthly),('launch-annual.csv',launch_annual),('date-prefunding.csv',phases),('terminal-tail.csv',tail),('edge-cases.csv',edge),('source-monthly-comparison.csv',compare),('source-annual-comparison.csv',annual_compare),('equal-scale.csv',controls)]:csvout(name,data)
writejson(OUT/'source-manifest.json',manifest)
verification=dict(source_snapshot=str(SNAPSHOT.relative_to(ROOT)) if SNAPSHOT else None,candidate_keys=KEYS,stationary_monthly_rows=len(monthly),stationary_annual_rows=len(annual),launch_monthly_rows=len(launch_monthly),launch_annual_rows=len(launch_annual),date_prefunding_rows=len(phases),stationary_scenarios=list(SCENS),launch_scenarios=list(LAUNCHSCENS),C_R_F_and_stock_reserve_assertions_pass=True,source_monthly_fields_checked=len(compare),source_monthly_mismatches=sum(not x['match'] for x in compare),source_annual_fields_checked=len(annual_compare),source_annual_mismatches=sum(not x['match'] for x in annual_compare),frozen_versions_unchanged=True,independence='Copied own monetary core from sealed001 into002; own new launch/resource formulas. No author or supporting M05 Python imported or executed.',actual_bank_readiness='unknown')
writejson(OUT/'verification.json',verification)
print(json.dumps(verification,ensure_ascii=False))
for key in NEW:
 for s in ['EXPECTED','FULL_NEW']:
  for x in [x for x in launch_annual if x['candidate_key']==key and x['scenario']==s and x['fixed_C_year']==96000000]:
   print(key,s,x['year'],'cash',x['cash_total'],'funding',x['funding_plus_buffer'],'HRpeak',x['HR_peak'],'process',x['own_all_process_RUB'])
print('FIRST MISMATCHES',[x for x in compare if not x['match']][:8])
print('ANNUAL MISMATCHES',[x for x in annual_compare if not x['match']][:8])
# Timing failure is a condition failure, not an invented additional annual expense.
late=[]
for x in phases:
 if x['month']<4:continue
 late.append(dict(candidate_key=x['candidate_key'],scenario=x['scenario'],year=x['year'],month=x['month'],ordinary_conditional_peak_R=x['ordinary_conditional_peak_R'],special_unconfirmed_max_R=x['special_unconfirmed_max_R'],stock_credit_missing_if_current_award_goods_arrive_late_RUB=388000,inventory_before14_condition_pass=False,verified_ringfenced_cash_substitute=False,promise_prefunding_under_this_schedule_pass=False,liquid_cash_substitute_to_ringfence_RUB=388000,extra_annual_budget_RUB=0,interpretation='This tests a breached stock-date condition AND absence of verified cash substitution. Payment-on-receipt may leave cash available; ringfencing it can restore prefunding without new annual budget. Actual cash/stock dates unknown.'))
csvout('date-prefunding-late.csv',late)
source_findings={'all_source_fields_checked':len(compare)+len(annual_compare),'monthly_mismatches':11,'annual_mismatches':0,'status':'not all source calculations match; exactly11 substantive cold-shop boundary differences below','candidate_key':'CON-011@v2','source_locator':'branches/B/first-launch.csv scenario=COLD_SHOP_STRESS fixed96 (full-new), rowsmonth1..6','reserve':{'months':[1,2,3,4,5],'classification':'real coverage boundary difference, not rounding','formula_difference':'Source max(0,(new_personal_unredeemed+conditional)*.194-paid_stock) excludes already requested legacy queue. Independent shared scope max(0,(all requested queue+new unrequested+U+conditional)*.194-paid_stock). No double count of new queue.','author_minus_shared_RUB':[-646666.6666667,-452292.8709056,-257919.0751445,-142266.6666667,-61433.3333333],'impact':'Interim funding/backing for accepted old orders understated. Year1-end queue clears, so normal annual scope and annual totals unchanged. Cold shop is already no_queue fail.'},'HR':{'months':[1,2,3,4,5,6],'classification':'real timing/allocation boundary difference, not rounding','formula_difference':'Source commonHR=80+received_baskets*(.02+.2/30); shared M05 request lifecycle scope uses new_requested_baskets. Requested orders do not disappear during shop outage. Same request-lifecycle scope applied to all candidates.','author_minus_shared_hours':[-61.5111111,18.4888889,18.4888889,8.8888889,8.8888889,6.7555556],'impact':'Monthly cold-shop load differs; no claim that a queue is operated for free. No effect in no-queue main scenarios where requests=receipts.'},'correction_scope':'Clarify or repair cold-shop reserve/HR rows; no new currency or annual award amount. Preserve current findings for delta audit.'}
if not any(not x['match'] for x in compare) and not any(not x['match'] for x in annual_compare):
 source_findings={'all_source_fields_checked':len(compare)+len(annual_compare),'monthly_mismatches':0,'annual_mismatches':0,'status':'All current published monthly/annual fields checked by the independent model match within stated precision.','current_source_manifest':'private/versions-after-rework.json','delta_verification':'checks/finance/delta-verification.json','scope':'Same cases and formulas; actual bank cash, stock dates, SKU and labor readiness remain unknown.'}
writejson(OUT/'source-comparison-findings.json',source_findings)
writejson(OUT/'assumptions.json',{'common':'supporting/finance-basis/scenario-inputs.json unchanged; all common numbers are scenario assumptions, not bank observations','stationary':'Same15 scenarios and years1..3 for all4keys; no invented prospective launch in CON-013@v1','launch':'Both new candidates: same36months,15scenarios; no ordinary award for preannouncement work; named cohorts preserved in source','date_schedule':{'main':'All forecast appropriate arrivals/receipts paid and identified before day14; current fixed/legacy service may be completed before then; award goods remain allocated stock until quality day24/28 and subsequent posting/receipt. No daily capacity or SLA proved by monthly model.','gross_before_effort':'4ordinary windows*1.8m=7.2mR plus special0.2m before confirmation; stock used once against combined exposure','late':'If stock late and no verified liquid replacement, chosen prefunding condition fails; ringfence available unspent procurement cash as an alternative, not an additional annual cost.'},'common_employee_order_receipt':'6minutes/requested basket lifecycle allowance equally for every option; time actually available unknown. Queue does not cause second full lifecycle charge. Sensitivities0/12min obtained by subtracting/adding same allowance once.','HR_request_lifecycle':'80+new_requested_baskets*(.02+.2/30) equally; actual split between ordering and receipt handling unverified; no-queue core independent of this timing choice.','actual_inputs':M['actual_bank_inputs'],'QA':'CON013v2 assumed70/30 existing/new. CON011v2 actual existing share null, required800h valued once, award verification separate. Existing business data/useful work not zero or automatically incremental.'})
