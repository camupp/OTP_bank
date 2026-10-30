"""Author scenario check of CON-006@v2. Stdlib; writes only branch B.
M01 frozen JSON; M02 common addendum. This is not independent finance approval.
"""
from pathlib import Path
import re,json,csv,hashlib,math
P=Path(__file__).resolve().parent
R=P.parent.parent
text=(R/'inputs/context.md').read_text()
M=json.loads(re.search(r'### Полные общие параметры M01\s+```json\s+(.*?)\s+```',text,re.S).group(1))
EPS=1e-5

def sim(s,mode='M01',year=1,opening=None):
 p=dict(M['common'],**s['overrides']);p.update(I_C_per_year=0,F_grant_per_quarter_R=0,R_awarded_per_quarter=0)
 if opening:p.update(C0=opening['C_close'],R0=opening['R_close'],opening_supplier_payables_rub=opening['AP_close'])
 merch=.8 if mode=='M02_MERCH' else .2
 k=.76 if mode=='M02_MERCH' else p['basket_cost_to_nominal']
 u=1000*k*p['purchase_price_multiplier']
 shares=[.3,.7] if mode=='M02_REGION' else [.6,.4]
 cap=[1800,1200]
 stock=list(opening['stock_close']) if opening and mode!='M01' else [600.,400.]
 C,Rc,J=p['C0'],p['R0'],0.
 qc=qr=qj=0.;prev=0.;Jissued=0.;ar=[]
 ow=[1/12]*12 if p['old_requests_calendar']=='uniform' else [.5]+[.5/11]*11
 for i in range(12):
  mo=i+1;Cstart,Rstart,Jstart=C,Rc,J
  x=p['R0']*p['R_conversion_fraction_old_and_new']*ow[i]
  dc=p['C0']*p['C_old_request_fraction']*ow[i]+x*p['converted_C_request_fraction']
  dr=p['R0']*p['R_direct_fraction_old_and_new']*ow[i]
  C+=x;Rc-=x
  issue=7200 if year==1 and mo==1 else (0 if year==1 else 600)
  J+=issue;Jissued+=issue
  due=600;V=dc/5000+due;U=dr/20000
  qc+=dc;qr+=dr;qj+=due
  # No region pooling: requested service on time is a separate constraint.
  outcap=min(cap[j]/shares[j] for j in range(2)) if mode!='M01' else 3000
  pc=min(qc,outcap*5000);qc-=pc;left=max(0,outcap-pc/5000)
  pj=min(qj,left);qj-=pj;J-=pj
  pr=min(qr,p['R_direct_capacity_units_per_month']*20000);qr-=pr
  C-=pc;Rc-=pr
  # Full request (not restricted service) determines procurement obligation.
  if mode=='M01':
   goods=V*u;log=0.;stockend=list(stock);order=[0,0]
  else:
   order=[]
   for j in range(2):
    demand=V*shares[j];target=[600,400][j]
    rec=max(0,math.ceil((demand+target-stock[j]-1e-9)/500))*500
    order.append(rec);stock[j]+=rec-demand
   goods=sum(order)*u;log=V*merch*150;stockend=list(stock)
  cash=(p['opening_supplier_payables_rub'] if mo==1 else 0)+.75*goods+.25*prev+log
  ap=.25*goods
  hr=80+.02*V+.1*U+36+(16 if year==1 and mo==1 else 0)+(V*merch*2/60 if mode!='M01' else 0)
  manager=124;author=60;recipient=20
  r_hours=8*U;r_cash=r_hours*1000*.25;hrcash=hr*1000*.2
  ar.append(dict(scenario=s['id'],mode=mode,year=year,month=mo,C_open=Cstart,R_open=Rstart,J_open=Jstart,C_requested=dc,R_requested=dr,conversion=x,C_redeemed=pc,R_redeemed=pr,C_close=C,R_close=Rc,J_issued=issue,J_due=due,J_served=pj,J_close=J,J_overdue=qj,C_queue=qc,R_queue=qr,baskets_required=V,R_units_required=U,goods_received=sum(order),segment_1_received=order[0],segment_2_received=order[1],order_month=mo-1,goods_rub=goods,logistics_rub=log,procurement_rub=goods+log,cash_rub=cash,AP_close=ap,stock_1=stockend[0],stock_2=stockend[1],HR_hours=hr,HR_cash_rub=hrcash,R_hours=r_hours,R_cash_rub=r_cash,manager_hours=manager,author_hours=author,recipient_hours=recipient,region_1_demand=V*shares[0],region_2_demand=V*shares[1],on_time=V<=outcap+EPS and U<=200+EPS and hr<=220+EPS))
  assert min(C,Rc,J,stockend[0],stockend[1])>=-EPS
  assert abs(C-Cstart-x+pc)<EPS and abs(Rc-Rstart+x+pr)<EPS and abs(J-Jstart-issue+pj)<EPS
  prev=goods
 total=lambda k:sum(r[k] for r in ar)
 ans=dict(scenario=s['id'],mode=mode,year=year,C_open=p['C0'],R_open=p['R0'],C_close=C,R_close=Rc,J_issued=Jissued,J_close=J,stock_close=list(stock),AP_open=p['opening_supplier_payables_rub'],AP_close=ap,procurement_rub=total('procurement_rub'),cash_rub=total('cash_rub'),goods_rub=total('goods_rub'),logistics_rub=total('logistics_rub'),HR_hours=total('HR_hours'),HR_cash_rub=total('HR_cash_rub'),R_cash_rub=total('R_cash_rub'),R_hours=total('R_hours'),manager_hours=1488,author_hours=720,recipient_hours=240,peak_HR=max(r['HR_hours'] for r in ar),peak_baskets=max(r['baskets_required'] for r in ar),peak_R_units=max(r['R_units_required'] for r in ar),on_time=all(r['on_time'] for r in ar),C_queue=qc,R_queue=qr,J_overdue=qj)
 ans['budget30']=max(ans['procurement_rub'],ans['cash_rub'])<=30000000+EPS
 ans['budget34']=max(ans['procurement_rub'],ans['cash_rub'])<=34000000+EPS
 ans['HR_cash_envelope']=ans['HR_cash_rub']<=750000+EPS
 ans['R_cash_envelope']=ans['R_cash_rub']<=3000000+EPS
 assert abs(ans['cash_rub']-ans['AP_open']-ans['procurement_rub']+ans['AP_close'])<EPS
 return ans,ar

if __name__=='__main__':
 annual=[];months=[]
 for s in M['scenarios']:
  for mode in ['M01','M02_CORE']:
   a,rows=sim(s,mode);annual.append(a);months.extend(rows)
 for mode in ['M02_MERCH','M02_REGION']:
  a,rows=sim(M['scenarios'][0],mode);annual.append(a);months.extend(rows)
 for mode in ['M01','M02_CORE']:
  opening=next(a for a in annual if a['mode']==mode and a['scenario']=='CORE')
  for y in range(2,6):
   a,rows=sim(M['scenarios'][0],mode,year=y,opening=opening);annual.append(a);months.extend(rows);opening=a
 for f,rows in [('annual.json',annual),('monthly.json',months)]:
  (P/f).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 for f,rows in [('annual.csv',annual),('monthly.csv',months)]:
  with (P/f).open('w') as out:
   w=csv.DictWriter(out,list(rows[0]));w.writeheader();w.writerows(rows)
 # Voluntary deferral: no annual accrued entitlement, one protected active J.
 deferred=[dict(year=y,J_open=0 if y==1 else 7200,J_new=7200 if y==1 else 0,J_redeemed=0,J_close=7200,protected_unit_rights=7200) for y in range(1,6)]
 (P/'deferral.json').write_text(json.dumps({'classification':'sensitivity; no personal expiry, no claim of cash saving or achieved behaviour','all_personally_defer':deferred,'administrative_delay':'Does not shift next eligibility; creates overdue obligation and can create J>one per person; scenario rejected, no cancellation of rights.'},ensure_ascii=False,indent=2)+'\n')
 v=dict(status='arithmetic_checked_not_finance_gate',annual_rows=len(annual),monthly_rows=len(months),sha256_frozen_context=hashlib.sha256((R/'inputs/context.md').read_bytes()).hexdigest(),checks=['C/R/J stock-flow and nonnegative stocks','cash=AP_open+procurement-AP_close','year2-5 C/R/AP/inventory carry','full demand procurement never reduced by queues','M02 fractional normalized regional units and500 batches'],limits=['Two synthetic segments, no actual catalog/ledger','M02 excludes inbound delivery capacity and queue-rework cost','personal service calendar and employer-delay restitution require implementation validation','No independent source validation or business effect measured'])
 (P/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([a for a in annual if a['scenario']=='CORE' and a['year']<=2],ensure_ascii=False,indent=2))
