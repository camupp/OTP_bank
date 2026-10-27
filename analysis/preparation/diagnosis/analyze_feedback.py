"""Read-only XLSX analysis. Run with bundled Python; outputs stay beside this script.

Unit: one source row/response, not a person. No deduplication in primary statistics.
Theme flags are a transparent rule-based first pass with explicit manual overrides.
"""
from pathlib import Path
import csv, json, re, hashlib, collections, statistics, datetime, random
import openpyxl

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=next((ROOT/'knowledge/raw').glob('задание*/*.xlsx'))
SHEET='старая-2026'
EXPECTED_SOURCE_SHA256='787a4adf74f3ff9ab52396515e49e5bf7ffa88569fcd0fa654ba8934841420fe'

def dump_csv(name,rows,fields=None):
    if fields is None:fields=list(rows[0]) if rows else []
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def text_value(v):
    if v is None:return ''
    if isinstance(v,float) and v.is_integer():return str(int(v))
    return str(v)
def norm(t):return re.sub(r'\s+',' ',t.strip().casefold().replace('ё','е'))

THEMES={
 'assortment':('Ассортимент товаров и выбор',r'ассорт|ассотт|разнообраз|расшир.{0,25}(выбор|список)|больш[еий].{0,25}(выбор|товар|подар|приз)|добав.{0,25}(товар|подар|приз)|нов.{0,15}(товар|мерч|подар|приз)|выбирать не из|выбрать не|^товары$|книг|одежд|толстов|футбол|свитшот|худи|жилет|носк|ручк|рюкзак|сумк|посуд|кружк|термо|канцеляр|зонт|практичн|брелок|пауэр|шоппер|ежедневник|шапк|банан|пижам|плед|брюк|рубаш|поло|игруш|блокнот|дождев|плав|космет|лосин|ветров|техник|аксессуар|^мерч$|мерча|флешк|ремувк'),
 'certificates':('Сертификаты: общий запрос, марки или номиналы',r'сертиф|серти|сертфик|сетифик|сетрифик|подарочн.{0,10}карт|универсальн.{0,10}карт|озон|оз[оа]н|ozon|вайл|ва[йи]лд|wildber|wildberries|яндекс|маркет|золот.{0,10}яблок|\bзя\b|магнит|пятероч|перекрест|спортмастер|вкусвилл|детск.{0,8}мир|летуаль|л.этуаль|рив.{0,5}гош|ашан|dns|днс|ситилинк'),
 'availability':('Наличие, пополнение и доступ к остаткам',r'налич|поступ|попол|появля|появлен|заканчив|законч|отсутств|дефицит|не хватает|нет в |нет сертифик|нет мерч|раскуп|разбира|разобра|не успев|доступност|всегда.{0,15}(были|был|есть)|постоянн.{0,15}(были|был|есть)|ожидан.{0,20}(сертиф|поступ|появ)|ожида.{0,20}(сертиф|поступ|появ)|лимит'),
 'price_value':('Цена в валюте и достижимость наград',r'цен[ауые]|стоим|дорог|дороже|дешев|сниз|снижен|пониз|завыш|комисси|курс.{0,10}(коин|обмен)|обмен.{0,12}руб|соотношен|скид|распрод|накоп|копить|коплю|копятся|не хватает.{0,15}(коин|балл|монет)|много.{0,10}(коин|балл)'),
 'delivery':('Получение, доставка и ожидание заказа',r'достав|получен|получать|получил|получила|получить|получени|ожидан|долго|быстр|срок|скорост|привоз|приходит|приходил|пришел|пришла|отправк|выдач|самовывоз|отделени|почт|курьер'),
 'ux_information':('Интерфейс, поиск, информация и коммуникации',r'интерф|поиск|фильтр|сортир|категор|навигац|удобств|удобн|сайт|портал|приложен|отображ|карточ|описан|фотограф|фото|картин|уведом|оповещ|информац|размерн.{0,6}сет|размер.{0,15}указ|раздел|инструкц|обновлен|добав.{0,10}избран|избранн|корзин|статус|отслеж|рассыл|обратн.{0,8}связ|промокод|паспорт|персональн.{0,10}данн|перс.{0,5}данн|автозаполн|заполнен.{0,10}данн|согласован|активац|аутентифик|истори.{0,15}(начисл|списан)|завис|система вис|анонс|пояснен|поступлен.{0,10}заяв'),
 'quality_function':('Качество, соответствие и работоспособность награды',r'качеств|брак|порва|слом|дефект|сгор|истек|не работа|не подош|не подход|просроч|не актив|не действ|не соотв|плох.{0,10}материал|мал[оа]мер|большемер'),
 'earn_recognition':('Начисление, обмен благодарностями и правила валюты',r'зарабат|заработ|начисл|получ.{0,12}(коин|балл|рукоин)|благодарност|рукоин|спасибо.{0,12}(отправ|коллег)|перевод.{0,12}(коин|монет)|дарить.{0,12}(коин|монет)|активност|поощрен|премир|мотивац|руководител|задани|тест|курс.{0,15}(прох|назнач)|участи.{0,10}(опрос|мероприят)'),
 'access_rules':('Лимиты покупок, доступность по ролям и нематериальные награды',r'ограничен|лимит|равноправ|грейд|отгул|дэй|дей.?оф|day.?off|удаленк|удаленн.{0,8}дн|опоздан|опаздан'),
 'positive':('Явная положительная оценка или отсутствие запроса изменений',r'все (хорошо|отлично|супер|класс|замечательно|устраивает|нравится|идеально|прекрасно|ок)|меня все устраивает|всем довол|все понрав|все устра|все супер|^спасибо[! .]*$|улучш.{0,12}не (нуж|над)|ничего.{0,10}(менять|улучшать)|нарекан.{0,6}нет|замечан.{0,6}нет|пожелан.{0,6}нет|претензи.{0,6}нет|нет (нарекан|замечан|пожелан|претензи)|^классно[! .]*$|очень довол'),
}

def initial_codes(text):
    t=norm(text)
    if not t:return [],'missing'
    if not re.search('[а-яa-z]',t) or t in {'да','нет','ок','ok','норм','нормально','хорошо','отлично','ничего','нет.','нет!','не знаю','затрудняюсь ответить'}:
        return [],'no_specific_content'
    codes=[k for k,(_,pat) in THEMES.items() if re.search(pat,t)]
    # Mere positive statements about delivery or store should not inflate problem themes.
    if 'positive' in codes and not re.search(r'но |хот|больше|расшир|добав|сниз|нуж|хорошо бы|не |пока|если|жел|почаще|выстав|сертиф|поступ|налич',t):
        codes=['positive']
    if not codes:return ['unclear'],'unclear'
    return codes,'positive_only' if codes==['positive'] else 'substantive'

def main():
    wb=openpyxl.load_workbook(SOURCE,data_only=False,read_only=False);ws=wb[SHEET]
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if source_hash!=EXPECTED_SOURCE_SHA256:
        raise ValueError('Source version changed: review source and update the declared version before recomputing.')
    raw=list(ws.iter_rows(min_row=5,max_row=ws.max_row,values_only=True))
    full_groups=collections.defaultdict(list);response_groups=collections.defaultdict(list)
    rows=[];issues=[];marker_counts=collections.Counter()
    for rn,v in enumerate(raw,5):
        full_groups[tuple(v)].append(rn);response_groups[tuple(v[2:])].append(rn)
        row={'source_row':rn,'locator':f'{SHEET}!A{rn}:T{rn}','date':v[1].isoformat()[:10] if isinstance(v[1],datetime.datetime) else text_value(v[1])}
        for label,a,b in [('convenience',2,7),('delivery',7,12),('purchase',12,17),('recommend',17,19)]:
            selections=[j for j,x in enumerate(v[a:b]) if str(x).strip()=='V'];unknown=[(a+j+1,text_value(x)) for j,x in enumerate(v[a:b]) if x is not None and str(x).strip() not in {'','V'}]
            marker_counts.update(text_value(x) for x in v[a:b])
            value=((5-selections[0]) if label!='recommend' else ['yes','no'][selections[0]]) if len(selections)==1 else ''
            row[label]=value if len(selections)==1 and not unknown else ''
            row[label+'_status']='valid' if len(selections)==1 and not unknown else 'missing' if not selections and not unknown else 'invalid'
            if row[label+'_status']!='valid':issues.append({'source_row':rn,'block':label,'status':row[label+'_status'],'selected_count':len(selections),'unknown_markers':json.dumps(unknown,ensure_ascii=False)})
        row['comment']=text_value(v[19]);row['comment_locator']=f'{SHEET}!T{rn}';row['comment_storage_type']=type(v[19]).__name__
        codes,kind=initial_codes(row['comment']);row['initial_codes']=';'.join(codes);row['codes']=row['initial_codes'];row['content_class']=kind;row['manual_review']='no';row['manual_note']=''
        rows.append(row)
    overrides={};review_rows=[];by_source_row={r['source_row']:r for r in rows}
    decisions=list(csv.DictReader((OUT/'manual_decisions.tsv').open(encoding='utf-8'),delimiter='\t')) if (OUT/'manual_decisions.tsv').exists() else []
    by_text={by_source_row[int(d['source_row'])]['comment'].strip():d for d in decisions}
    for r in rows:
        if r['comment'].strip() in by_text:
            d=by_text[r['comment'].strip()];c=d['codes'];kind='no_specific_content' if d['intent']=='none' else 'unclear' if c=='unclear' else 'positive_only' if c=='positive' else 'substantive'
            rec={'source_row':r['source_row'],'representative_source_row':d['source_row'],'comment_locator':r['comment_locator'],'initial_codes':r['initial_codes'],'final_codes':c,'content_class':kind,'intent':d['intent'],'note':d['note']}
            overrides[r['source_row']]=rec;review_rows.append(rec)
    dump_csv('manual_review.csv',review_rows)
    for r in rows:
        if r['source_row'] in overrides:
            o=overrides[r['source_row']];r['codes']=o['final_codes'];r['content_class']=o['content_class'];r['manual_review']='yes';r['manual_note']=o['note'];r['intent']=o['intent']
        else:r['intent']='unreviewed'
    dup=[]
    for idx,(key,members) in enumerate(sorted(full_groups.items(),key=lambda x:x[1][0]),1):
        if len(members)>1:dup.append({'group':f'D{idx:04}','count':len(members),'excess_rows':len(members)-1,'source_rows':';'.join(map(str,members)),'first_locator':f'{SHEET}!A{members[0]}:T{members[0]}','has_comment':bool(text_value(key[-1]).strip())})
        for r in rows:
            if r['source_row'] in members:r['exact_group_first_row']=members[0];r['exact_group_size']=len(members)
    dump_csv('responses.csv',rows);dump_csv('data_issues.csv',issues);dump_csv('exact_duplicate_groups.csv',dup)
    ratings=[]
    sensitivity=[]
    for scope,sub in [('all_rows',rows),('one_row_per_exact_A_T_pattern',[r for r in rows if r['exact_group_first_row']==r['source_row']])]:
        for col in ['convenience','delivery','purchase','recommend']:
            vs=[r[col] for r in sub if r[col]!=''];n=len(vs);ct=collections.Counter(vs)
            for value in ([5,4,3,2,1] if col!='recommend' else ['yes','no']):
                ratings.append({'scope':scope,'question':col,'value':value,'count':ct[value],'valid_n':n,'all_n':len(sub),'percent_valid':round(ct[value]/n*100,4)})
            sensitivity.append({'scope':scope,'question':col,'valid_n':n,'missing_n':len(sub)-n,'mean':round(statistics.mean(vs),6) if col!='recommend' else '', 'top_score_or_yes_n':ct[5 if col!='recommend' else 'yes'],'top_score_or_yes_pct':round(ct[5 if col!='recommend' else 'yes']/n*100,6),'low_1_3_n':sum(ct[x] for x in [1,2,3]) if col!='recommend' else ''})
    dump_csv('rating_distributions.csv',ratings);dump_csv('rating_summary.csv',sensitivity)
    themes=[];nonempty=sum(bool(r['comment'].strip()) for r in rows);substantive=sum(r['content_class']=='substantive' for r in rows)
    for k,(label,pat) in THEMES.items():
        members=[r for r in rows if k in r['codes'].split(';')]
        meaningful=sum(r['content_class'] in ['substantive','positive_only'] for r in rows)
        themes.append({'theme':k,'label':label,'response_count':len(members),'pct_all_1913':round(len(members)/len(rows)*100,4),'pct_nonempty_comments':round(len(members)/nonempty*100,4),'denominator_nonempty':nonempty,'pct_meaningful_comments':round(len(members)/meaningful*100,4),'denominator_meaningful':meaningful,'manual_reviewed_members':sum(r['manual_review']=='yes' for r in members),'locators':';'.join(r['comment_locator'] for r in members)})
    dump_csv('theme_counts.csv',themes)
    monthly=[]
    for month in sorted(set(r['date'][:7] for r in rows)):
        sub=[r for r in rows if r['date'].startswith(month)]
        rr={'month':month,'response_rows':len(sub),'nonempty_comments':sum(bool(r['comment'].strip()) for r in sub)}
        for col in ['convenience','delivery','purchase']:
            vs=[r[col] for r in sub if r[col]!=''];rr[col+'_n']=len(vs);rr[col+'_mean']=round(statistics.mean(vs),6) if vs else ''
        monthly.append(rr)
    dump_csv('monthly_descriptive.csv',monthly)
    comment_groups=collections.defaultdict(list)
    for r in rows:
        if r['comment'].strip():comment_groups[r['comment'].strip()].append(r['source_row'])
    unique=[{'source_row':rs[0],'n_same_text':len(rs),'all_rows':';'.join(map(str,rs)),'text':t,'initial_codes':next(r['initial_codes'] for r in rows if r['source_row']==rs[0])} for t,rs in comment_groups.items()]
    dump_csv('unique_comments.csv',unique)
    audit={'source_path':SOURCE.relative_to(ROOT).as_posix(),'source_sha256':source_hash,'sheet':SHEET,'range':'A1:T1917','data_range':'A5:T1917','rows':len(rows),'dates_min':min(r['date'] for r in rows),'dates_max':max(r['date'] for r in rows),'date_sorted':all(rows[i]['date']<=rows[i+1]['date'] for i in range(len(rows)-1)),'unique_name_values':len(set(v[0] for v in raw)),'name_is_valid_person_key':False,'marker_counts':dict(marker_counts),'formulas':sum(c.data_type=='f' for rr in ws for c in rr),'hidden_rows':[i for i,d in ws.row_dimensions.items() if d.hidden],'hidden_columns':[i for i,d in ws.column_dimensions.items() if d.hidden],'merged_ranges':[str(x) for x in ws.merged_cells.ranges],'comment_nonempty':nonempty,'comment_missing':len(rows)-nonempty,'unique_comment_texts':len(comment_groups),'comment_storage_types':dict(collections.Counter(type(v[-1]).__name__ for v in raw)),'exact_row_unique_patterns':len(full_groups),'exact_duplicate_groups':len(dup),'exact_duplicate_excess_rows':sum(d['excess_rows'] for d in dup),'exact_duplicate_rows_in_groups':sum(d['count'] for d in dup),'same_response_ignoring_date_unique_patterns':len(response_groups),'content_classes':dict(collections.Counter(r['content_class'] for r in rows)),'manually_reviewed_rows':sum(r['manual_review']=='yes' for r in rows),'assumption':'All source rows retained; matching anonymized rows are not assumed to identify duplicate people.'}
    audit['manually_reviewed_unique_texts']=len(by_text)
    audit['meaningful_comments']=sum(r['content_class'] in ['substantive','positive_only'] for r in rows)
    (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    (OUT/'source_manifest.json').write_text(json.dumps({'source':audit['source_path'],'sha256':source_hash,'sheet':SHEET,'data_range':'A5:T1917','script':'analyze_feedback.py','run_python':'bundled Python with openpyxl','source_modified':False},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(audit,ensure_ascii=False,indent=2));print(json.dumps(sensitivity,ensure_ascii=False,indent=2));print('initial theme counts',[(r['theme'],r['response_count']) for r in themes])

if __name__=='__main__':main()
