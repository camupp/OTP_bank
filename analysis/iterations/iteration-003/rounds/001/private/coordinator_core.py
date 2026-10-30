"""Independent CORE formulas; no author/financial model imported."""
from pathlib import Path
import json,re,math
R=Path(__file__).resolve().parents[1]
s=(R/'inputs/context.md').read_text()
blocks=re.findall(r'```json\s*(.*?)```',s,re.S)
M=next(json.loads(b) for b in blocks if 'C_old_request_fraction' in b)
if 'common' not in M:M=M['M01']
p=M['common'];results=[]
for key,emission,wq,new_j,extra in [('BASELINE',p['I_C_per_year'],p['R_awarded_per_quarter'],0,0),('CON-005@v1',48000000,0,0,40),('CON-005@v2',0,0,1200,24),('CON-006@v2',0,0,600,36)]:
 C,Rbal=p['C0'],p['R0'];units=[];direct=[]
 for m in range(12):
  W=wq*p['R_award_month_shares_in_quarter'][m%3];I=emission/12
  X=(p['R0']/12+W)*p['R_conversion_fraction_old_and_new']
  dc=p['C0']/12*p['C_old_request_fraction']+I*p['C_new_request_fraction']+X*p['converted_C_request_fraction']
  dr=(p['R0']/12+W)*p['R_direct_fraction_old_and_new']
  C+=I+X-dc;Rbal+=W-X-dr;units.append(dc/5000+new_j);direct.append(dr/20000)
 unitcost=940;purchase=[u*unitcost for u in units]
 cash=1000000+sum(purchase)-.25*purchase[-1]
 stock=[600,400];receipts=[];hr=[]
 for m,u in enumerate(units):
  received=0
  for j,(share,target) in enumerate(zip([.6,.4],[600,400])):
   need=u*share+target-stock[j];batches=max(0,math.ceil((need-1e-7)/500));n=batches*500
   stock[j]+=n-u*share;received+=n
  receipts.append(received)
  hr.append(80+.02*u+.1*direct[m]+extra+.2*u*2/60+(16 if key=='CON-006@v2' and m==0 else 0))
 mpurchase=[n*940+u*.2*150 for n,u in zip(receipts,units)]
 # Treat logistics paid current month and goods75/25 as B author does; compare consolidated convention explicitly.
 mcash=1000000+sum(n*940 for n in receipts)-.25*receipts[-1]*940+sum(u*.2*150 for u in units)
 results.append({'candidate_key':key,'C_close':C,'R_close':Rbal,'units':sum(units),'M01_procurement':sum(purchase),'M01_cash':cash,'M02_receipts':sum(receipts),'M02_inventory_close':sum(stock),'M02_procurement':sum(mpurchase),'M02_cash_goods75_25_logistics_current':mcash,'M02_HR_peak':max(hr)})
(R/'private/coordinator-core.json').write_text(json.dumps({'scope':'Independent CORE formulas only. M02 logistics cash currently paid; final finance conventions compared separately. No queues or financial gates assigned.','results':results},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
