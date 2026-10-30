"""Independent output reconciliations; does not import the author model."""
from pathlib import Path
import csv,json,collections
P=Path(__file__).resolve().parent
A=list(csv.DictReader((P/'annual-results.csv').open()))
M=list(csv.DictReader((P/'monthly-results.csv').open()))
T=list(csv.DictReader((P/'ten-year-results.csv').open()))
def num(x,k):return float(x[k])
errors=[]
def check(ok,msg):
    if not ok:errors.append(msg)
for a in A:
    key=(a['scenario'],a['fund_R_year'],a['year'])
    ms=[m for m in M if (m['scenario'],m['fund_R_year'],m['year'])==key]
    check(len(ms)==12,f'months{key}')
    check(abs(num(a,'C_open')+num(a,'R_open')+num(a,'C_fixed_issued')+num(a,'R_awarded')-num(a,'C_redeemed')-num(a,'C_close')-num(a,'R_close'))<1e-5,f'currency{key}')
    check(abs(sum(num(m,'cash_rub') for m in ms)-num(a,'procurement_plus_logistics_cash_rub'))<1e-5,f'cash{key}')
    check(abs(sum(num(m,'F_granted_R') for m in ms)-num(a,'R_awarded'))<1e-5,f'fund_grants{key}')
    check(abs(sum(num(m,'R_awarded') for m in ms)-num(a,'R_awarded'))<1e-5,f'fund_awards{key}')
    check(all(abs(num(m,'F_close'))<1e-5 for m in ms if int(m['month'])%3==0),f'quarter_reset{key}')
    check(num(a,'new_R_reserve_close_rub')>=-1e-5,f'R_reserve{key}')
G=collections.defaultdict(list)
for t in T:G[(t['scenario'],t['fund_R_year'])].append(t)
for key,rows in G.items():
    for prev,nxt in zip(rows,rows[1:]):
        check(abs(num(prev,'C_close')-num(nxt,'C_open'))<1e-5,f'Ccarry{key}')
        check(abs(num(prev,'R_close')-num(nxt,'R_open'))<1e-5,f'Rcarry{key}')
        check(abs(num(prev,'inventory_close_units')-num(nxt,'inventory_open_units'))<1e-5,f'inventorycarry{key}')
def row(s,f=8000000):return next(x for x in A if x['scenario']==s and int(float(x['fund_R_year']))==f)
check(abs(num(row('LOW_FIXED96_FULL_NEW'),'C_fixed_issued')-96000000)<1e-5,'low_frequency_explicit')
check(abs(num(row('LOW_FIXED96_FULL_NEW'),'C_redeemed')-144000000)<1e-5,'all_new_plus20percentold')
check(abs(num(row('LOW_FIXED96_FULL_NEW'),'procurement_plus_logistics_cash_rub')-28033000)<1e-4,'known_low_full_new_cash')
check(abs(num(row('ALL_RIGHTS_100'),'consumed_landed_cost_rub')-68288000)<1e-4,'full_all_rights_cost')
check(row('FIXED_100')['budget30_cash_pass']=='False' and row('FIXED_100')['budget34_cash_pass']=='False','central_full_new_not_falsely_passed')
check(row('REGIONAL_80')['capacity_pass']=='False','regional_failure_visible')
check(row('JAN_OLD_50')['capacity_pass']=='False','concentration_failure_visible')
check(abs(num(row('NEW_R_USE_0'),'new_R_reserve_close_rub')-1552000)<1e-4,'zero_redemption_not_saved')
r={'status':'pass' if not errors else 'fail','annual_rows_checked':len(A),'monthly_rows_checked':len(M),'ten_year_rows_checked':len(T),'errors':errors,'scope':'independent CSV stock-flow/cash/carryover and explicit all-new/all-rights boundary checks'}
(P/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(r,ensure_ascii=False))
assert not errors
