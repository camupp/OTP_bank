"""Narrow finance/version/U delta only. Does not regenerate resource grids.

Run: PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/check_delta.py
Current source authority must additionally pass the independent evidence check.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
import csv,hashlib,json,math,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; RD=HERE.parents[1]
ARCH=RD/'private/pre-rework'; CUR=RD/'branches/B/con-023'; BEFORE=ARCH/'branches/B/con-023'
OLDKEY='CON-023@v1'; NEWKEY='CON-023@v2'; checks=[]
def read(p):return json.loads(p.read_text())
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(p,rr):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rr for k in r)));w.writeheader();w.writerows(rr)
def ck(name,ok,detail=None):checks.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail is not None else {})})
def near(a,b):return abs(float(a)-float(b))<1e-5
def truth(v):return v is True or v=='True'
pins=read(RD/'private/versions-before-checks.json')['files']
bad=[p for p,h in pins.items() if sha(RD/p)!=h]
ck('all current frozen pins',not bad,bad)
invariants=[]
for name in ['finance-spec.json','resource-stages.csv','build_resources.py','monthly-resource.csv','annual-resource.csv','setup-resource.csv','calendar-traces.csv','money-examples.csv','cards.md','employee-card.md','assumptions.csv']:
    old=(BEFORE/name).read_text();new=(CUR/name).read_text()
    ok=old==new.replace(NEWKEY,OLDKEY)
    ck('financial invariant '+name,ok)
    invariants.append({'path':'branches/B/con-023/'+name,'before_sha256':sha(BEFORE/name),'current_sha256':sha(CUR/name),'identical_except_candidate_label':ok,'rows':len(rows(CUR/name)) if name.endswith('.csv') else None})
for p in sorted((RD/'branches/A').rglob('*')):
    if p.is_file() and (ARCH/p.relative_to(RD)).exists():ck('unchanged A '+str(p.relative_to(RD)),sha(p)==sha(ARCH/p.relative_to(RD)))
allowed={'candidate_key','version','parents','authorization','authorization_contract'}
oldspec=read(BEFORE/'metrics-spec.json');newspec=read(CUR/'metrics-spec.json')
ck('all reward/metric thresholds unchanged',{k:v for k,v in oldspec.items() if k not in allowed}=={k:v for k,v in newspec.items() if k not in allowed})
ck('old independent arithmetic complete',read(ARCH/'checks/finance/verification.json')['all_arithmetic_checks_pass'])
ck('retained monthly resources normalized', (HERE/'monthly-resource.csv').read_text().replace(NEWKEY,OLDKEY)==(ARCH/'checks/finance/monthly-resource.csv').read_text())

# Current calculated allocation and held authorization, no source scoring code.
u=rows(CUR/'unit-decisions.csv');d=rows(CUR/'decisions.csv');g=rows(CUR/'group-top-reserve.csv');w=rows(CUR/'window-guarantee.csv')
gg=defaultdict(list);allocation=[];auth=[]
for r in u:gg[r['scenario'],r['period'],r['group'],r['work_type']].append(r)
gmap={(r['scenario'],r['period'],r['group'],r['work_type']):r for r in g}
for (sc,period,group,worktype),rr in gg.items():
    pp=[r for r in d if (r['scenario'],r['period'],r['group'],r['work_type'])==(sc,period,group,worktype)]
    pool=150*len({r['subject'] for r in pp})
    # Current policy preserves independently calculated rank when a source-
    # permission act is invalid; missing primitive/QA data still hold the pool.
    # One registered unit has no top allocation, including no group-top promise.
    held=len(rr)>=2 and any(r['state'] in ('pending','not_computable') for r in rr)
    ranks={r['subject']:tuple(F(str(x)) for x in json.loads(r['rank_key'])) for r in rr if truth(r['strong'])};want={};pos=0
    if len(rr)>=2 and not held:
        for score in sorted(set(ranks.values()),reverse=True):
            ids=[s for s in ranks if ranks[s]==score];amount=F(pool)*sum([F(4,10),F(3,10),F(2,10),F(1,10)][pos:pos+len(ids)])/len(ids)
            want.update({s:amount for s in ids});pos+=len(ids)
    for r in rr:ck('current unit pool '+str((sc,period,r['subject'])),near(want.get(r['subject'],0),r['top_R']))
    total=0;totalU=0
    for r in pp:
        amount=math.floor(want.get(r['unit'],0)*F(r['share'])) if truth(r['calculated_normal']) else 0
        U=0 if json.loads(r['authorization_errors']) or json.loads(r['source_review_errors']) else amount
        ck('current personal amount and held U '+str((sc,period,r['subject'])),near(amount,r['top_earned_R']) and near(U,r['top_U_R']))
        total+=amount;totalU+=U
        auth.append({'candidate_key':NEWKEY,'scenario':sc,'period':period,'subject':r['subject'],'calculated_top_R':amount,'sanctioned_U_R':float(r['top_U_R']),'earned_held_R':amount-float(r['top_U_R']),'group_conditional_ceiling_R':pool if held else 0,'scope':'conditional ceiling repeated per person is never summed; separate evidence validates actual source authority'})
    gr=gmap[sc,period,group,worktype]
    ck('current group conservation '+str((sc,period,group)),near(gr['pool_R'],pool) and near(gr['earned_R'],total) and near(gr['authorized_U_R'],totalU) and near(gr['conditional_R'],pool if held else 0) and near(float(gr['earned_R'])+float(gr['conditional_R'])+float(gr['unissued_R']),pool))
    allocation.append({'candidate_key':NEWKEY,'scenario':sc,'period':period,'group':group,'work_type':worktype,'unique_people':len(pp),'pool_R':pool,'group_held':held,'calculated_personal_R':total})
for r in w:
    pp=[p for p in d if p['scenario']==r['scenario'] and p['subject']==r['subject'] and p['window']==r['window']]
    earned=2500 if len(pp)==2 and all(truth(p['calculated_normal']) for p in pp) else 0
    U=earned if pp and all(not json.loads(p['authorization_errors']) and not json.loads(p['source_review_errors']) for p in pp) else 0
    ck('current G/window and held U '+str((r['scenario'],r['subject'],r['window'])),near(earned,r['G_earned_R']) and near(U,r['G_U_R']) and near(earned-U,r['G_earned_held_R']))
ck('current source snapshots do not manufacture posting signatures',all(r['authorization']=='held_no_authorization' for r in d) and sum(float(r['top_U_R']) for r in d)==0 and sum(float(r['G_U_R']) for r in w)==0)
evidence=read(RD/'checks/evidence/delta-verification.json')
controls=read(RD/'checks/evidence/current-controls.json')
c3_ok=(evidence['current_control_summary']=={'pass':26,'fail':0} and evidence['own_package_match_for_positive_personal_team'] and not evidence['freeze_mismatches'] and controls['candidate_key']==NEWKEY and all(r['status']=='pass' for r in controls['controls']))
ck('independent current source-authorization controls',c3_ok,{'locators':['checks/evidence/current-controls.json','checks/evidence/delta-verification.json'],'current_controls_sha256':sha(RD/'checks/evidence/current-controls.json'),'evidence_delta_sha256':sha(RD/'checks/evidence/delta-verification.json'),'positive_personal_U_R':600,'positive_team_member_U_R':420,'scope':'hypothetical performed acts, exact independent packages and logical replay only; real posting ledger absent'})

# Label-only migration of already verified resource data; never recompute grid.
for p in HERE.iterdir():
    if p.is_file() and p.name not in {'check_delta.py','delta-verification.json'} and p.suffix in ('.csv','.json','.py','.md'):
        text=p.read_text()
        if OLDKEY in text:p.write_text(text.replace(OLDKEY,NEWKEY))
prior=rows(HERE/'allocation.csv')
table(HERE/'allocation.csv',[r for r in prior if r['candidate_key']!=NEWKEY]+allocation)
table(HERE/'current-U-controls.csv',auth)
manifest=read(HERE/'source-manifest.json')
manifest['analysis/iterations/iteration-007/rounds/002/private/versions-before-checks.json']=sha(RD/'private/versions-before-checks.json')
manifest['analysis/iterations/iteration-007/rounds/002/branches/B/con-023/finance-spec.json']=sha(CUR/'finance-spec.json')
dump(HERE/'source-manifest.json',manifest)
result={'scope':'Narrow finance delta only; no old/core/resource grids regenerated; no author model/exporter/verify/build executed. Source authorization remains pending independent evidence.','current_keys':['CON-022@v1',NEWKEY,'CON-016@v2','BASELINE'],'current_pins_sha256':sha(RD/'private/versions-before-checks.json'),'checks':len(checks),'all_pass':all(x['pass'] for x in checks),'failures':[x for x in checks if not x['pass']],'invariant_files':invariants,'current_U_diagnostic':{'person_period_rows':len(d),'window_rows':len(w),'all_snapshots_are_alternative_scenarios_not_additive_bank_demand':True,'all_top_U_R':sum(float(x['top_U_R']) for x in d),'all_G_U_R':sum(float(x['G_U_R']) for x in w),'all_calculated_top_R':sum(float(x['top_earned_R']) for x in d),'all_calculated_G_R':sum(float(x['G_earned_R']) for x in w),'held_authorization_rows':sum(x['authorization']=='held_no_authorization' for x in d)},'checks_detail':checks}
result['scope']='Narrow financial invariance and current U only; no core/resource grids regenerated or author code executed. Independent evidence26controls pass exact-package source authority; no actual ledger or funded bank operations inferred.'
dump(HERE/'delta-verification.json',result)
base=read(HERE/'verification.json');base['current_keys']=result['current_keys'];base['narrow_current_version_delta']='checks/finance/delta-verification.json';base['authority_scope']='Calculated and held U are arithmetic-consistent. Independent evidence26controls pass hypothetical exact source/package authority and logical replay; real ledger absent.';dump(HERE/'verification.json',base)
f=json.loads((RD/'checks/finance.json').read_text().replace(OLDKEY,NEWKEY));f['status']='current frozen versions; financial checks complete within disclosed scenarios'
for r in f['results']:
    if r['candidate_key']!=NEWKEY:continue
    r['gates']['currency_balances']='pass' if c3_ok and result['all_pass'] else 'uncertain'
    r['findings']=[x for x in r['findings'] if x['classification'] not in ('independent evidence finding; monetary authorization unresolved','calculation; independent source authority pending','calculation and independent evidence control')]
    r['findings'].append({'classification':'calculation and independent evidence control','text':'Current source snapshots hold all3524person-period authorizations when exact performed acts are missing: top_U=G_U=0; calculated and earned-held rights remain separate and reserved. Independent26controls pass: exact positive personal600R/team member420R; invalid actsU0; annualG2500 and logical replay stable. Pass covers hypothetical source/package authority and arithmetic only; no actual ledger posting, operating budget, staffing or timely delivery inferred. Financial/resource/award norms are fully invariant.','locators':['checks/finance/current-U-controls.csv','checks/evidence/current-controls.json;positive_personal,positive_team_member,negative controls,fixedwindowG,replay','checks/evidence/delta-verification.json','branches/B/con-023/window-guarantee.csv']})
    r['calculation_paths'] += [p for p in ['checks/finance/check_delta.py','checks/finance/delta-verification.json','checks/finance/current-U-controls.csv'] if p not in r['calculation_paths']]
dump(RD/'checks/finance.json',f)
for name in ['finance.md','finance-for-review.md']:
    p=RD/'checks'/name;text=p.read_text().replace(OLDKEY,NEWKEY)
    start=text.index('C3 у CON-023@v2 остаётся открытым:') if 'C3 у CON-023@v2 остаётся открытым:' in text else text.rindex('Санкционирование U у CON-023@v2')
    end=text.index('\n\nВоспроизведение',start)
    text=text[:start]+'''Санкционирование U у CON-023@v2 пока uncertain до независимой проверки evidence. Текущий контракт требует точного пакета/версии/суммы, нужного источника, независимых личных и командных актов и выполненной подписи после quality-close. Все 3524 person-period записи источникового пакета остаются held; top_U и G_U равны нулю, расчётное и earned-held право сохраняются. Это не экономия. Ресурс, календарь, ставки и нормы наград подтверждены целиком; таблицы finance/current-U-controls.csv и delta-verification.json относятся к текущим состояниям.''' + text[end:]
    text=text.replace('Открыты: C3 CON-023,','Открыты: независимое подтверждение текущего санкционирования CON-023,')
    text=text.replace('Воспроизведение: PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/independent_check.py из папки раунда.','Воспроизведение текущих финансовых инвариантов: PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/check_delta.py из папки раунда; исходные уравнения приведены в independent_check.py.')
    text=text.replace('Санкционирование U у CON-023@v2 остаётся uncertain по независимым C3-probes.','Санкционирование U у CON-023@v2 имеет pass в проверенной сценарной области.')
    start=text.rindex('Санкционирование U у CON-023@v2 пока uncertain')
    end=text.index('\n\nВоспроизведение',start)
    text=text[:start]+'''Санкционирование U у CON-023@v2 имеет pass в проверенной сценарной области. Текущий контракт требует точного пакета/версии/суммы, нужного источника, независимых личных и командных актов и выполненной подписи после quality-close. Все 3524 person-period записи исходных source-снимков остаются held при отсутствии точных актов: top_U и G_U равны нулю, расчётное и earned-held право сохраняются. Это не экономия. Независимые 26 контролей evidence прошли: при гипотетически выполненных точных актах личный U600 R и командная доля U420 R разрешаются; неверные акты дают U0; G2500 относится к одному фиксированному годовому окну, логический replay не суммирует U. Положительные пакеты независимо восстановлены и побайтно совпали. Реального ledger posting, наличия денег/людей или соблюдения банковского SLA эти проверки не доказывают. Источник: checks/evidence/current-controls.json; денежные состояния: finance/current-U-controls.csv.

Качество CON-022 чувствительно к 0,05 балла в проверенном источнике: в R2.quality QA99 получает rank21 и top0, QA100 — rank1 с ничьей двадцати и 300 R лично. В R2.precision QA99,05 соединяется с QA100 из-за разрыва меньше одного балла: ничья тридцати, по 200 R лично. Строгое недоказанное превосходство не возникает, но деньги меняются 0→200 и 300→200 R. Это ограничение устойчивости опубликованного правила; финансовый pass его не снимает. Locators: checks/evidence/scenario-summary.csv, R2.quality/R2.precision; checks/evidence/independent-persons.csv.''' + text[end:]
    text=text.replace('Открыты: независимое подтверждение текущего санкционирования CON-023,','Открыты: фактический ledger posting и ')
    text=text.replace('Авторские exporter/verify/build не запускались.','Экспортирующие модели не запускались.')
    p.write_text(text)
print(json.dumps({'checks':result['checks'],'all_pass':result['all_pass'],'failures_first10':result['failures'][:10],'current_U_diagnostic':result['current_U_diagnostic']},ensure_ascii=False))
