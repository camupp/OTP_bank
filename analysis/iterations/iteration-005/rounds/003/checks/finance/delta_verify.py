#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single prose/SHA delta only; never executes the financial model."""
from pathlib import Path
import hashlib,json,re

P=Path(__file__).resolve().parent; R=P.parent.parent
BEFORE=R/'private/before-targeted-rework'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
old=js(BEFORE/'versions-before-checks.json')
new=js(R/'private/versions-after-rework.json')
assert new==js(R/'private/versions-before-checks.json')
assert len(old)==len(new)==38
for path,h in old.items(): assert sha(BEFORE/path)==h,path
for path,h in new.items(): assert sha(R/path)==h,path
changed=[path for path,h in new.items() if h!=old[path]]
assert set(changed)=={'branches/B/concept-015.md','branches/B/changes.md'}
path='branches/B/concept-015.md'
b=(BEFORE/path).read_text(); a=(R/path).read_text()
assert b.count('с lower это42500 в год')==1
assert a==b.replace('с lower это42500 в год','с lower это42000 в год')
assert 'с lower это42000 в год' in a.splitlines()[44]
ordinary=4*(10000+500); special=2*7500
assert ordinary==42000 and ordinary+special==57000

# Byte comparison only. No personal examples, grid, or 39k checks re-executed.
unchanged_calculations=[]
for q in sorted((BEFORE/'checks/finance').iterdir()):
    if not q.is_file() or q.name in ['finance-for-review.md','source-manifest.json','delivery-verification.json']:continue
    target=P/q.name
    assert q.read_bytes()==target.read_bytes(),q.name
    unchanged_calculations.append({'path':'checks/finance/'+q.name,'sha256':sha(target),'byte_identical':True})

d=js(R/'checks/finance.json')
for result in d['results']:
    if result['candidate_key']!='CON-015@v1':continue
    result['artifact_consistency']='checked_final_sources; prose_arithmetic_issue_closed'
    for finding in result['findings']:
        if finding['classification']=='open_prose_arithmetic_issue':
            finding['classification']='closed_prose_arithmetic_issue'
            finding['statement']=('Финальная строка45 исправлена: обычный максимум '
                '4×(10000+500)=42000 R/год; с2×7500 special=57000. '
                'Cap97000, потолок24млн, календарь и расчётные файлы неизменны. '
                'Проверены точная замена42500→42000, новыеSHA и36неизменных авторскихфайлов; '
                'core и личные примеры повторно не рассчитывались.')
    result['calculation_paths']=list(dict.fromkeys(result['calculation_paths']+[
        'checks/finance/delta_verify.py','checks/finance/delta-verification.json']))
d['open_findings']=[]
d['closed_findings']=[{'candidate_key':'CON-015@v1','issue':'ordinary annual prose42000; all channels57000',
    'locator':'branches/B/concept-015.md:45','status':'closed','delta':'checks/finance/delta-verification.json'}]
d['delta_verification']='checks/finance/delta-verification.json'
write(R/'checks/finance.json',d)

oldparagraph=('В concept-015.md:45 есть опечатка: обычный максимум **42000 = 4×(10000+500)**, написано 42500. '
    'Общий максимум со special 57000 указан верно; cap97000 сохранён и не связывает выплаты. '
    'Потолок 24 млн и валютный баланс не затронуты. Авторский файл не изменён. '
    'В дополнительных n10/n100 fixtures есть совпадения округлённых Q: выплата 2496/24996 корректна, '
    'теоретические разные ранги дают 2500/25000.')
newparagraph=('Опечатка в concept-015.md:45 исправлена и замечание закрыто: обычный максимум '
    '**42000 = 4×(10000+500)**, со special **57000 = 42000+15000**. '
    'Финальные SHA проверены; 36 остальных авторских файлов и все расчётные файлы неизменны. '
    'Cap97000, потолок 24 млн, календарь и финансовые gates сохранены. '
    'Денежный core, личные примеры и первоначальные 39390 проверок повторно не запускались. '
    'В дополнительных n10/n100 fixtures есть совпадения округлённых Q: выплата 2496/24996 корректна, '
    'теоретические разные ранги дают 2500/25000.')
for target in [R/'checks/finance.md',P/'finance-for-review.md']:
    text=target.read_text()
    assert oldparagraph in text or newparagraph in text
    text=text.replace(oldparagraph,newparagraph)
    link='finance/delta-verification.json' if target.parent==R/'checks' else 'delta-verification.json'
    sentence=f'\nТочечная проверка финальных источников: [delta-verification]({link}).\n'
    if sentence not in text:text+=sentence
    target.write_text(text)

manifest=js(P/'source-manifest.json')
manifest['final_author_source_freeze']={
    'path':'private/versions-after-rework.json','sha256':sha(R/'private/versions-after-rework.json'),
    'equals_current_versions_before_checks':True,'files':new}
manifest['targeted_delta']={
    'changes':[{'path':path,'before_sha256':old[path],'after_sha256':new[path]} for path in changed],
    'unchanged_files':36,'verification':'checks/finance/delta-verification.json',
    'initial_manifest':'private/before-targeted-rework/checks/finance/source-manifest.json'}
for path in changed:manifest['sha256'][path]=new[path]
write(P/'source-manifest.json',manifest)

delta={'status':'pass','scope':'single prose correction and final source hashes only',
    'before_freeze':'private/before-targeted-rework/versions-before-checks.json',
    'final_freeze':'private/versions-after-rework.json == private/versions-before-checks.json',
    'exact_single_replacement':True,'line':45,'ordinary_R_year':ordinary,
    'special_R_year':special,'all_channels_R_year':ordinary+special,
    'changed_files':[{'path':path,'before_sha256':old[path],'after_sha256':new[path]} for path in changed],
    'unchanged_author_files':36,'unchanged_calculation_files':unchanged_calculations,
    'core_reexecuted':False,'personal_examples_reexecuted':False,
    'initial_39390_checks_reexecuted':False,'initial_arithmetic_status':'pass, unchanged historical verification.json',
    'financial_gates_unchanged':True,'open_findings':[],
    'remaining_limits':'All initial M05 scenario boundaries and actual bank readiness uncertainty remain.'}
write(P/'delta-verification.json',delta)
for result in d['results']:
    for path in result['calculation_paths']: assert (R/path).exists(),path
for q in [R/'checks/finance.md',P/'finance-for-review.md']:
    for path in re.findall(r'\]\(([^)]+)\)',q.read_text()): assert (q.parent/path).exists(),path
write(P/'delivery-verification.json',{'status':'pass','phase':'final targeted prose delta',
    'contract_keys':[x['candidate_key'] for x in d['results']],
    'calculation_paths_exist':True,'report_links_exist':True,
    'final_author_hashes_verified':True,'initial_calculations_unchanged':True,
    'delta_verification':'checks/finance/delta-verification.json','open_findings':[],
    'output_sha256':{str(q.relative_to(R)):sha(q) for q in [R/'checks/finance.json',R/'checks/finance.md',P/'finance-for-review.md',P/'model.py',P/'verification.json',P/'delta-verification.json']}})
print(json.dumps({'status':'pass','closed':'42500→42000;42000+15000=57000',
    'unchanged_author_files':36,'unchanged_calculation_files':len(unchanged_calculations),
    'core_reexecuted':False,'open_findings':[]},ensure_ascii=False))
