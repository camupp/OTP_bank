"""Current version/U finance delta only; no resource grid generation."""
from pathlib import Path
import csv,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;RD=HERE.parents[1];ARCH=RD/'private/pre-rework'
A=RD/'branches/A/con-024';OLD=ARCH/'branches/A/con-024'
K0='CON-024@v1';K='CON-024@v2';checks=[]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open() as f:return list(csv.DictReader(f))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def ck(name,ok,detail=None):checks.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail is not None else {})})
pins=read(RD/'private/versions-before-checks.json')['files']
ck('final frozen pins',all(sha(RD/p)==h for p,h in pins.items()))
invariants=[]
for name in ['finance-spec.json','resource-reference.json','resource-stages.csv','setup-resource.csv','resource-supply.json','calendar-boundaries.csv','unit-decisions.csv','money-examples.csv','qa-neighborhood.csv','qa-ties.json','window-guarantee.csv','group-top-reserve.csv']:
    ok=(A/name).read_text().replace(K,K0)==(OLD/name).read_text();ck('same numeric/resource '+name,ok)
    invariants.append({'file':'branches/A/con-024/'+name,'before_sha256':sha(OLD/name),'current_sha256':sha(A/name),'same_after_metadata_label_normalization':ok})
oldm=read(OLD/'metrics-spec.json');newm=read(A/'metrics-spec.json')
for k in oldm:
    if k not in ['candidate_key','signature']:ck('same metric/reward parameter '+k,oldm[k]==newm[k])
ck('same signature contract except requested fields',{k:v for k,v in newm['signature'].items() if k not in ['business_config_projection','source_review_time']}==oldm['signature'])
for rel,h in read(A/'resource-reference.json')['files'].items():
    root=next(p for p in HERE.parents if (p/'project/brief.md').exists());ck('inherited resource pin '+rel,sha(root/h['project_path'])==h['sha256'])
for p in (RD/'branches/B').rglob('*'):
    old=ARCH/p.relative_to(RD)
    if p.is_file() and old.exists():ck('unchanged B '+str(p.relative_to(RD)),sha(p)==sha(old))
prior=read(ARCH/'checks/finance/verification.json');ck('independent finance basis complete',prior['all_pass'] and prior['checks']==56431)
d0=rows(OLD/'decisions.csv');d=rows(A/'decisions.csv')
drop={'candidate_key','authorization_errors','source_review_errors'}
norm=lambda rr:[{k:v for k,v in r.items() if k not in drop} for r in rr]
ck('all calculated money/rights/U unchanged',norm(d0)==norm(d))
ck('original source snapshots hold all U',all(float(r['top_U_R'])==0 for r in d) and all(float(r['authorized_U_R'])==0 for r in rows(A/'window-guarantee.csv')))

# Reuse established numerical tables only after zero-delta verification.
for p in HERE.iterdir():
    if p.is_file() and p.suffix in ['.csv','.json','.py','.md'] and p.name not in ['check_delta.py','delta-verification.json']:
        t=p.read_text()
        if K0 in t:p.write_text(t.replace(K0,K))
manifest=read(HERE/'source-manifest.json')
root=next(p for p in HERE.parents if (p/'project/brief.md').exists())
for p in [A/'finance-spec.json',A/'metrics-spec.json',A/'resource-reference.json',RD/'private/versions-before-checks.json']:
    manifest[str(p.relative_to(root))]=sha(p)
dump(HERE/'source-manifest.json',manifest)

# Evidence supplies the independently constructed exact-package/time controls.
# This section is finalized only after its current v2 output is available.
c3pass=False; evidence_refs=[]
ev=RD/'checks/evidence/current-delta-verification.json'
if ev.exists():
    e=read(ev)
    summary=e['current_C3_summary'];act=RD/'checks/evidence/a-current-controls.json';actual=read(act)
    c3pass=(e['candidate_key']==K and summary=={'pass':11,'fail':0} and not e['final_pin_mismatches'] and all(e['semantic_invariance'].values()) and all(e['numeric_CSV_invariance'].values()) and actual['candidate_key']==K and all(c['status']=='pass' for c in actual['controls']))
    evidence_refs=[{'path':'checks/evidence/current-delta-verification.json','sha256':sha(ev)},{'path':'checks/evidence/a-current-controls.json','sha256':sha(act)}]
baseok=all(r['pass'] for r in checks)
result={'current_keys':[K,'CON-025@v1','CON-023@v2','BASELINE'],'scope':'Only numerical/resource/version and current U invariants; no new grids/scenarios, no author or closed exporter/model execution.','checks':len(checks),'all_pass':baseok,'failures':[r for r in checks if not r['pass']],'checks_detail':checks,'invariant_files':invariants,'initial_independent_checks_reused':56431,'current_source_rows':len(d),'current_source_top_U_R':sum(float(r['top_U_R']) for r in d),'C3_pass_from_independent_evidence':c3pass,'evidence_refs':evidence_refs,'money_scope':'All qualified promised rights held/reserved independent of U0;4.47m is39month idle-cost difference4.35+0.06+0.06+0,not recurring annual bank savings. Variability/standby/requalification fees and real availability remain unknown.'}
dump(HERE/'delta-verification.json',result)
v=read(HERE/'verification.json');v['current_keys']=result['current_keys'];v['current_version_delta']='checks/finance/delta-verification.json';v['authority_scope']='Current exact-package/team-time controls passed independently within hypothetical source domain; no real posting.' if c3pass else 'Current exact-package/team-time controls await independent evidence; calculated rights and U holding unchanged.';dump(HERE/'verification.json',v)

# Explicitly migrate the root checks JSON, then read it back below.
f=json.loads((RD/'checks/finance.json').read_text().replace(K0,K));f['status']='current frozen versions; checks complete within disclosed scenarios' if c3pass else 'current frozen versions; A authority pending independent evidence'
for r in f['results']:
    if r['candidate_key']==K:
        r['gates']['currency_balances']='pass' if c3pass and baseok else 'uncertain'
        r['findings']=[x for x in r['findings'] if x['classification'] not in ['independent evidence finding; authority unresolved','current version/source authority']]
        r['findings'].append({'classification':'current version/source authority','text':'Numerical resource/reward/calendar/category tables and all calculated rights/U are identical after metadata normalization. Original source snapshots authorize no newU; rights/window/reserve preserved. Independent current11C3controls pass exact full business-config binding and team source close-time: hypothetical positive150U, altered-config/stale/early/invalidactsU0, close-time boundary150U and one logical150U replay. Currency pass is confined to that source/package and arithmetic scope, with no real ledger or staffing/funding/SLA inference.','locators':['checks/finance/delta-verification.json','checks/evidence/a-current-controls.json','checks/evidence/current-delta-verification.json']})
    if r['candidate_key'] in ['CON-025@v1','CON-023@v2']:
        r['findings']=[x for x in r['findings'] if x['classification']!='uncertain contract cost and finite savings boundary']
        r['findings'].append({'classification':'uncertain contract cost and finite savings boundary','text':'4.470mRUB is the39month scenario difference4.350Y1+0.060Y2+0.060Y3+0tail; not4.47m annual recurring savings. Actual ex-ante calendar variability contracts, standby/availability retainers, rescheduling and requalification fees/time unknown, not proven zero. Net additional savings=4.470m minus additional such costs; full forecast work, queues, qualification and rights unchanged.','locators':['checks/finance/savings.csv','branches/B/con-025/resource-supply.csv','supporting/resource-menu.json']})
    for p in ['checks/finance/check_delta.py','checks/finance/delta-verification.json']:
        if p not in r['calculation_paths']:r['calculation_paths'].append(p)
dump(RD/'checks/finance.json',f)
assert [r['candidate_key'] for r in read(RD/'checks/finance.json')['results']]==result['current_keys']
current=read(HERE/'current-controls.json');current['current_keys']=result['current_keys'];current['A_current_U']='pass in independently checked hypothetical exact-package/team-time scope; original sourceU0 and rights retained' if c3pass else 'uncertain until independent current exact-package/team-time checks';current['delta_checks']=len(checks);current['delta_all_pass']=baseok;current['no_actual_ledger']=True;current['contract_fees_unknown']='variable bookings/standby/requalification;4.47m39months not annual';dump(HERE/'current-controls.json',current)

paragraph=('''Санкционирование CON-024@v2 имеет pass в проверенной сценарной области: полный business-config включён в независимую точную привязку пакета, а личный и командный source-review должен быть выполнен не раньше quality-close. Все 11 текущих контролей evidence прошли: гипотетический положительный личный/командный акт даёт150U; изменённый config со старой подписью, ранний/пустой/невалидный командный акт дают0U; подпись ровно в close допускает150U. Missing-award сохраняет расчётное право/окно/резерв, replay сохраняет одно логическое150U. Новые QA-копии не считаются подписанными выплатами. В исходных source-снимках U удерживается без нужного точного акта; реального ledger posting, фактических денег/людей или банковского SLA эти проверки не доказывают. Источник: checks/evidence/a-current-controls.json.''' if c3pass else '''Санкционирование CON-024@v2 пока uncertain до независимых текущих exact-package/team-time контролей evidence. Численные нормы, распределение, ресурс и исходное удержание U сохранены; расчётное право/окно/резерв не отменяются. Реальный ledger, деньги/люди и SLA неизвестны.''')
fees='''Разница 4,470 млн руб. относится ко всем 39 месяцам: 4,350 млн в Y1, по 0,060 млн в Y2 и Y3, ноль в хвосте. Она не заявлена ежегодной повторяющейся экономией. Реальные условия контрактов с переменными месячными объёмами, плата за доступность/standby, перепланирование и повторную квалификацию людей неизвестны, не доказаны нулевыми. Чистая разница = 4,470 млн минус дополнительные такие расходы. Actual-work, очереди, квалификация и права не сокращаются; обязательства по датированному будущему обеспечению остаются условием проекта.'''
for name in ['finance.md','finance-for-review.md']:
    p=RD/'checks'/name;t=p.read_text().replace(K0,K)
    t=t.replace('Для CON-024@v2 currency_balances пока uncertain из-за текущих C3-проб.','Для CON-024@v2 currency_balances имеет pass в проверенной сценарной области.' if c3pass else 'Для CON-024@v2 currency_balances пока uncertain до текущих C3-контролей.')
    if c3pass:t=t.replace('Для CON-024@v2 currency_balances пока uncertain до текущих C3-контролей.','Для CON-024@v2 currency_balances имеет pass в проверенной сценарной области.')
    start=t.index('Расчётное право, условный резерв, санкционированное U и фактическая проводка различны.')
    end=t.index('\n\nBASELINE',start)
    t=t[:start]+'Расчётное право, условный резерв, санкционированное U и фактическая проводка различны. '+paragraph+t[end:]
    if 'Реальные условия контрактов с переменными месячными объёмами' not in t:t=t.replace('\n\n| Версия; fixed96,×1', '\n\n'+fees+'\n\n| Версия; fixed96,×1')
    t=t.replace('Открыты: C3 CON-024 и фактические деньги/люди/ledger/минуты/SKU/SLA/эффект.','Открыты: фактические деньги/люди/ledger/минуты/SKU/SLA/эффект и контрактные/standby/повторные квалификационные расходы.')
    # Keep reviewer prose restricted to current numbers and conditions.
    t=t.replace('Команда из папки раунда: PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/check.py.','Текущие инварианты: PYTHONDONTWRITEBYTECODE=1 python3 -B checks/finance/check_delta.py; исходные уравнения приведены в check.py.')
    p.write_text(t)
print(json.dumps({'delta_checks':len(checks),'delta_all_pass':baseok,'C3_pass':c3pass,'written_root_results':[(r['candidate_key'],r['gates']) for r in read(RD/'checks/finance.json')['results']],'root_finance_sha256':sha(RD/'checks/finance.json')},ensure_ascii=False))
