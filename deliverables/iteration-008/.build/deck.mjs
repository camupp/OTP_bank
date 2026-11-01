import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
import {slides} from './content.mjs';
const root='/Users/davatoros/Desktop/OTP_bank';
const out=path.join(root,'deliverables/iteration-008');
const build=path.join(out,'.build');
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#14392F',green:'#006B45',lime:'#C7E943',muted:'#526A63',paper:'#FAFCFA',rule:'#D6E0D9',red:'#A63D2F'};
const readable=t=>String(t).replace(/([а-яё])(?=\d)/gi,'$1 ').replace(/(\d)(?=[а-яё])/gi,'$1 ').replace(/(\d)([CRG])(?=\b|\/|\s|\+|$)/g,'$1 $2').replace(/([,;])(?=[A-Za-zА-Яа-яё])/g,'$1 ').replace(/(CSI|ER)(?=\d)/g,'$1 ').replace(/вгод/g,'в год').replace(/вm(?=\d)/g,'в m').replace(/(?<=\d)FTE/g,' FTE').replace(/Июль(?=\d)/g,'Июль ');
const text=(s,t,x,y,w,h,size=26,bold=false,color=C.ink)=>{
 const q=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=readable(t);q.text.style={fontSize:size,typeface:'Arial',bold,color,insets:0,wrap:'square',autoFit:'none',verticalAlignment:'top'};return q;
};
const s=p.slides.add();s.background.fill=C.ink;
text(s,'ОТП Мания',64,92,1120,100,64,true,'#FFFFFF');
text(s,'Понятные критерии\nдополнительного поощрения',64,224,1110,180,52,true,'#FFFFFF');
text(s,'Рабочий результат получает признание\nв действующей программе банка',66,445,1050,90,30,false,'#DCE9DE');
text(s,'Cup Moscow 2026   /   Команда: [не указана]',66,630,1100,34,20,false,'#DCE9DE');
s.speakerNotes.text='Адресное развитие существующей ОТП Мании. Корпоративные активности, кошельки, магазин и старые права сохраняются. Источники: кейс PDF с.9–19; Transcript.md 39:18–39:55 и41:50. Название команды пока отсутствует.';
await fs.mkdir(build,{recursive:true});
const summary=JSON.parse(await fs.readFile(path.join(build,'summary.json'),'utf8').catch(()=>'{"selected":"A","A_setup":0,"A_recurring_year":0,"B_setup":692000,"B_recurring_year":0,"team":null}'));
if(summary.team){
 s.shapes.items[s.shapes.items.length-1].text=`Cup Moscow 2026   /   ${summary.team.name}`;
}
function base(d,num){
 const s=p.slides.add();s.background.fill=C.paper;
 text(s,d.title,64,42,1152,112,42,true);
 text(s,(d.appendix?`Приложение ${d.appendix}   /   `:'')+d.source,64,658,1085,40,15,false,C.muted);
 text(s,String(num),1170,658,44,24,16,false,C.muted);
 s.speakerNotes.text=d.notes||d.source;return s;
}
function table(s,heads,rows,widths,{x=64,y=178,h=430,size=23}={}){
 const vals=[heads,...rows].map(row=>row.map(v=>typeof v==='string'?readable(v):v));
 const q=s.tables.add({rows:vals.length,columns:heads.length,left:x,top:y,width:widths.reduce((a,b)=>a+b,0),height:h,columnWidths:widths,values:vals});
 q.styleOptions={headerRow:true,bandedRows:false};
 q.cells.block({row:0,column:0,rowCount:vals.length,columnCount:heads.length}).assign({fill:'#FFFFFF',textStyle:{fontSize:size,typeface:'Arial',color:C.ink},margins:{left:9,right:9,top:7,bottom:6}});
 q.cells.block({row:0,column:0,rowCount:1,columnCount:heads.length}).assign({fill:C.ink,textStyle:{fontSize:size,typeface:'Arial',bold:true,color:'#FFFFFF'}});
 q.rows[0].height=72;
 for(let i=1;i<vals.length;i++)q.rows[i].height=(h-72)/(vals.length-1);
 q.borders.assign({fill:C.rule,width:0.7,style:'solid'});
 return q;
}
function para(s,label,body,x,y,w=540){text(s,label,x,y,w,38,28,true,C.green);text(s,body,x,y+47,w,130,26);}
slides.splice(7,0,{kind:'table',appendix:'А0',title:'Дерево причин задаёт проверяемые гипотезы',headers:['Уровень 1','Уровень 2','Уровень 3','Уровень 4 / проверка'],widths:[230,240,340,342],rows:[['Ценность\nпризнания','Понятное\nоснование','Связь работы с поощрением','Готовые критерии, мощность,\nприёмка и объяснение права.\nПредзамер понимания.'],['Ценность\nпризнания','Доступная\nнаграда','Ассортимент / запас / регион','Пригодный SKU до обещаний.\nДефицит, цена, срок исполнения.\nПроверка полного получения.'],['Ценность\nпризнания','Управляемое\nисполнение','Полнота источника и полномочия','Старые/новые права и резервы.\nОтвод, подписи, квитанция.\nКонтроль пиков и исключений.']],source:'Источник: диагностика отзывов, кейсс.15–19, Transcript17:11–17:58 и43:26–44:43. Причины — гипотезы, не причинные оценки.',notes:'Четыре уровня issue tree. Ценностьпризнания — верхний вопрос. Разныеветви отражают основание,награднуюценность иисполнение. Последнийуровень — механизмбарьера иконкретнаяпроверка. Данныепокупателей не доказываютпричинность/масштабпоштатувсехгипотез.'});
slides.push({kind:'funding',appendix:'А12',title:'Годовая модель обеспечивает весь E24-предел',source:'Источник: сохранённая M05, проверенные annual-three-year.csv и finance/delivery-summary.json. Все суммы — сценарные.',notes:'Денежнаягодоваямодель и39месячныйпервыйзапускраздельны. Год1–3обеспечиваетполныйE24предел. Касса,прирострезерва,буфер иSKUпоправка не складывают валюту/заказдважды. Комиссиинеизвестны. Операционныйресурсвэтоммостеотсутствует.'});
slides.push({kind:'currency',appendix:'А13',title:'C и R сходятся при конвертации и погашении',source:'Источник: сохранённый годовой ряд M05 и независимые finance-checks008. Единица: млн C или млн R, не рубли.',notes:'Сценарныеоткрывающиеостатки160млнC/40млнR. Новыеfixed96млнC/год, весьRконверт24млн/год. Переводмеждусотрудникаминеэмиссия,конвертацияR→C1:1сохраняетобщуюмассу. Fвыделен24/выдан24/невыдан0 — модельнаяграница,нефактбанка. Наличиеpendingвпервомзапускенеснижаетобеспечениеправ.'});
const expanded=slides.flatMap(d=>d.kind==='table'&&['А1','А4','А7','А8','А10'].includes(d.appendix)?[0,1].map(k=>({...d,appendix:d.appendix+(k?'б':'а'),rows:d.rows.slice(k*2,k*2+2)})): [d]);
const tableSlides=[];
for(const [index,d] of expanded.entries()){
 const n=index+2,s=base(d,n);
 switch(d.kind){
 case 'diagnosis':{
 text(s,'1061 непустой комментарий из 1913 строк отзывов',64,174,1152,38,25,true);
 const q=s.charts.add('bar',{position:{left:60,top:231,width:560,height:335},categories:['Сертификаты','Ассортимент','Информация','Начисления'],series:[{name:'Доля комментариев, %',values:[35.5,23.5,15.2,4.5],fill:C.green}],hasLegend:false,barOptions:{direction:'bar',gapWidth:90},xAxis:{textStyle:{fontSize:20,typeface:'Arial'},numberFormatCode:'0"%"'},yAxis:{textStyle:{fontSize:21,typeface:'Arial'}},dataLabels:{showValue:true,position:'outEnd',textStyle:{fontSize:21,typeface:'Arial'},numberFormatCode:'0.0"%"'},chartFill:C.paper,plotAreaFill:C.paper});
 para(s,'Основание признания','Разная регулярность руководителей\nи вопрос «за что R» в T1335.\nГипотеза: заранее понятные критерии.',680,230,510);
 para(s,'Доступная ценность','Выбор, наличие и получение награды.\nГипотеза: пригодная награда и проверка\nвсего пути до вручения.',680,410,510);
 text(s,'Темы могут пересекаться. Это отобранные отзывы после покупки, а не измерение охвата всего банка.',64,594,1140,46,20,false,C.muted);break;}
 case 'alternatives':
 table(s,['Подход','Связь с вкладом','Обычный доступ','Решение'],[
 ['Усмотрение\nруководителя','Решение руководителя\nбез общих критериев','Гарантии нет','Сохраняем основу.\nДобавляем критерии.'],
 ['Благодарность\n+ равный подарок','Признание отдельно.\nПодарок всем.','Всем одинаково','Заменяет будущие C/R.\nОтсев по границам задачи.'],
 ['Конкурс качества','Нет штрафов\nпри полном QA','Гарантия есть','Риск скрывать minor.\nСлабее связь с результатом.'],
 ['Принятый\nролевой результат','Результат при\nпригодном качестве','2500 R / 12 месяцев\nбез призового места','Выбранная механика.\nПроверяем внедрение.']
 ],[238,305,257,352],{y:178,h:380,size:23});
 text(s,'Практики «Звука» и ATB поддерживают разделение прав и общую инфраструктуру. Причинный эффект для ОТП не установлен.',64,591,1130,50,21,false,C.muted);break;
 case 'mechanism':
 table(s,['Работа','Обычный результат','Сильный результат'],[
 ['Поддержка','Принятый поток ≥1,00 мощности\nи пригодное качество','≥1,10 мощности\nпри том же качестве'],
 ['Бэк-офис','Тот же нормированный результат\nи ≥95% операций в срок','≥1,10 мощности\nпри тех же сроках и качестве'],
 ['Проект / аналитика','Целый результат принят и используется\nпо заранее заданной деловой цели','Выше локальной цели /\nготов к pre-read']
 ],[255,555,342],{y:180,h:300,size:24});
 text(s,'Два подходящих квартала одного закреплённого окна',64,508,1140,36,28,true,C.green);
 text(s,'2500 R один раз в 12 месяцев. Первая гарантия при запуске: m7–15.\nКонвертация R в C 1:1. Модель: 2500 C за сертификат 500 руб.',64,553,1140,66,25);
 text(s,'Весь будущий R-блок: 24 млн / год = 18 млн гарантия + 4,32 млн конкурс + 1,68 млн особый вклад.',64,625,1140,27,20,false,C.muted);break;
 case 'integration':
 table(s,['Кто','Действие в существующей работе','Дополнительный контроль'],[
 ['Сотрудник','Работает в очереди / трекере.\nВидит правило и свой статус.','Второй отчёт не нужен.\nОбращение по исключению.'],
 ['Руководитель /\nвладелец данных','Полный поток, приёмка и качество.','Цель до периода.\nСвой случай: внешний выпуск.'],
 ['HR / независимый\nуполномоченный','Расчёт права, отдельный выпуск.\nПроводка и сверка квитанции.','Разные роли и точная версия.\nПовтор ключа не новая выдача.']
 ],[260,490,402],{y:180,h:310,size:24});
 text(s,'Сохраняем портал, активности, кошельки, магазин и старые права.',64,528,1140,38,29,true,C.green);
 text(s,summary.selected==='A'?'Встраивание: контролируемые отчёты и реестры. Пакетный ввод предполагается.\nЕсли его нет, остаётся оплаченный ручной режим.':'Встраивание: CSV-приёмка, личная карточка, независимый маршрут и квитанция.\nНовые функции текущего портала заменяют механические сверки.',64,577,1140,64,24);break;
 case 'roadmap':
 table(s,['Подготовка\nm−5…−3','Теневой квартал\nm−2…0','Полное окно\nm1…6','Наградной цикл\nm7 и далее'],[
 ['HR, владельцы, IT.\nПоля, нормы, роли.\nSKU, деньги, резерв.\nВсё до обещаний.','Все три семейства.\nСверка расчётов.\nОшибки и отводы.\nБез начислений.','Обычная работа.\nДва квартала с QA.\nПрава и окна\nсохраняются.','Независимый акт.\nЗаказ и вручение.\nКогорта 1: m7.\nВсе 9: m7–15.']
 ],[288,288,288,288],{y:194,h:275,size:24});
 para(s,'Допуск к запуску','Полные данные и независимые роли.\nРесурс и награды до обещаний.',64,510,548);
 para(s,'Условие масштабирования','Пилот завершён получением награды.\nПики труда и ассортимент проверены.',680,510,530);break;
 case 'economics':{
 text(s,'Закупка и обеспечение наград',64,184,585,36,28,true,C.green);
 text(s,'31,684 млн руб.',64,245,600,74,54,true);
 text(s,'Год 1: касса + прирост резерва + буфер\nи поправка на сертификаты, до комиссий.\n34 млн руб. проходят. 30 млн руб. не проходят.',64,334,580,118,25);
 const setup=summary[summary.selected+'_setup']||0,rec=summary[summary.selected+'_recurring_year']||0;
 text(s,'Операционный ресурс',680,184,530,36,28,true,C.green);
 text(s,summary.selected==='A'?'Настройка: 3,990 млн руб.\nБронь: 19,500 млн руб. за 39 месяцев.\nВ ней добавка 180 тыс. руб. в год 1.\nНовая деятельность: 48 тыс. руб. в год.':`Настройка: ${(4.682).toFixed(3).replace('.',',')} млн руб.\nБронь: 19,500 млн руб. за 39 месяцев.\nВ ней добавка 180 тыс. руб. в год 1.\nНовая деятельность: 240 тыс. руб. в год.`,680,246,535,162,25);
 text(s,'Без пакетного ввода: ещё 6,060 млн руб. за 39 месяцев.',680,418,535,54,21,false,C.muted);
 text(s,'Область расчёта: 7200 человек, E24, 96 млн C корпоративных событий / год,\n20% старого погашения, базовые цены. Это допущения, не факты банка.',64,478,1150,62,22,false,C.muted);
 text(s,'Пилот: понимание правил и срок до награды. CSI 4,85 и ER 75% — цели кейса.\nРиски: скромная редкая награда, неполные данные, ресурс и доступность наград.',64,572,1150,66,24);break;}
 case 'team':{
 const team=summary.team;
 if(team){text(s,team.name,64,180,1152,60,36,true,C.green);table(s,['Участник','Роль в команде'],team.members.map(x=>[x.name,x.role]),[570,582],{y:267,h:330,size:29});}
 else {text(s,'Название команды: [не указано]',64,192,1150,60,36,true,C.green);table(s,['Участник','Роль в команде'],[['[Имя не указано]','[Роль не указана]'],['[Имя не указано]','[Роль не указана]'],['[Имя не указано]','[Роль не указана]']],[570,582],{y:290,h:280,size:28});text(s,'Состав 3–5 человек. Дополнительные строки заполняются только по данным команды.',64,603,1140,44,21,false,C.muted);}break;}
 case 'table': table(s,d.headers,d.rows,d.widths,{y:178,h:d.rows.length===2?400:410,size:22});tableSlides.push(n);break;
 case 'operations':
 table(s,['Операция','Отчёты и пакет','Адресные функции портала'],[
 ['Полнота и QA','Файл полного потока.\nСверка scope и актов.','CSV проверяет весь массив.\nЧеловек разбирает исключения.'],
 ['Расчёт и личный статус','Версия правил и реестр прав.\nПерсональная защищённая выгрузка.','Тот же расчёт.\nПриватная карточка с причиной.'],
 ['Отвод и выпуск','Внешний уполномоченный\nподписывает точный пакет.','Маршрут проверяет конфликт.\nПодписывает человек.'],
 ['Проводка и восстановление','Ключ и квитанция, сверка до/после.\nОплаченный ручной резерв.','Очередь и квитанция.\nРучной режим при отказе.']
 ],[245,445,462],{y:181,h:410,size:23});
 text(s,'В обоих способах профессиональный QA, персональный review и подписи сохраняются.\nГотовые данные не заменяют независимое решение о выпуске.',64,605,1150,48,21,false,C.muted);break;
 case 'costs':
 table(s,['Расход, млн руб.','Общая основа','Отчёты / пакет','Функции портала'],[
 ['Настройка, всего','3,990','3,990','4,682'],
 ['Новая деятельность / 12мес.','В прежней брони','0,048','0,240'],
 ['Бронь всех ролей /39мес.','19,320','19,500','19,500'],
 ['Setup +39мес., с полным\nпострочным ручным резервом','Не детализирован','29,550','30,242']
 ],[375,259,259,259],{y:184,h:330,size:23});
 text(s,'Без построчного резерва: 23,490 млн руб. для отчётов и 24,182 млн для портала.\nНовая кассовая бронь180тыс. вгод1 входит в19,500млн,не добавляется к ней ещё раз.',64,554,1150,79,25);break;
 case 'metrics':
 table(s,['Ветвь','Метрика и знаменатель','Период / проверка'],[
 ['Признание','Понимают критерии / ответившие.\nДоля ответов из всех приглашённых отдельно.','До старта и после квартала.\nПо ролям и регионам.'],
 ['Доступ к награде','Получили награду / получили право.\nМедиана и p90 дней от права до вручения.','По окнам и когортам.\nPending остаётся в наблюдении.'],
 ['Исполнение','Расхождения, неразрешённые/двойные выдачи.\nАпелляции и срок их закрытия.','Каждый выпуск.\nНезависимый контрольный расчёт.'],
 ['Экономика / цели','Касса и резерв раздельно, C/R/U/заказы.\nCSI 4,85 и ER 75% — цели кейса.','Месяц и год. Формулы CSI/ER\nсогласуются до пилота.']
 ],[235,535,382],{y:177,h:385,size:22});
 text(s,'Проверка эффекта: сопоставимые группы ролей, поэтапное включение и измерение до/после.\nПилот допускает отсутствие улучшения. HR friends & family проверяет удобство, не весь штат.',64,579,1150,66,23);break;
 case 'sources':
 para(s,'Факты программы','Кейс ОТП, физические с.4,9–19.\nTranscript.md:13:12–14:01,39:18–39:55,\n41:50,43:26–44:43,50:26,55:33.',64,185,560);
 para(s,'Данные и диагностика','XLSX, лист «старая-2026»,A5:T1917.\nanalysis/preparation/diagnosis/:\nsummary_for_inputs,ratings,themes,quotes.',680,185,530);
 para(s,'Механика и экономика','CON-025:cards,employee-card,finance-spec.\niteration-007/rounds/003/checks/finance.\niteration-008:checks,review,selection.',64,395,560);
 para(s,'Требования и метод','tg_info.txt:43–65;30102026_tg_chat:413–414.\nУчебник Changellenge:с.195–215,224–229,\n253–257,268–272. Структура и защита.',680,395,530);break;
 case 'funding':{
 const a=summary.procurement_and_currency||[];
 const f=(key)=>(a.length?a.map(x=>(x[key]/1e6).toFixed(3).replace('.',',')):['уточняется','уточняется','уточняется']);
 table(s,['Показатель, млн руб.','Год 1','Год 2','Год 3'],[['Касса: закупка и логистика',...f('cash_RUB')],['Прирост резерва прав',...f('reserve_delta_RUB')],['Буфер',...f('buffer_RUB')],['Сертификат500руб.: поправка',...f('certificate500_adjustment_RUB')],['Обеспечение до комиссий',...f('certificate500_funding_RUB')]],[540,204,204,204],{y:180,h:360,size:24});
 text(s,'Операционные затраты отдельно. При 34 млн руб. проходит раскрытая область.\nПри 30 млн руб. годы 1 и 2 не проходят. E24 заменяет весь будущий блок R.',64,576,1150,60,23);break;}
 case 'currency':{
 const a=summary.procurement_and_currency||[];
 const f=(key)=>(a.length?a.map(x=>(x[key]/1e6).toFixed(3).replace('.',',')):['уточняется','уточняется','уточняется']);
 table(s,['Остаток / поток, млн единиц','Год 1','Год 2','Год 3'],[['C на начало',...f('C_open')],['Корпоративные C начислены',...f('fixed_C_issued')],['R по всему конверту начислены',...f('R_posted')],['Конвертация R в C, 1:1',...f('R_to_C')],['C погашены',...f('C_redeemed')],['C на конец',...f('C_close')],['R на начало',...f('R_open')],['R на конец',...f('R_close')]],[540,204,204,204],{y:175,h:392,size:23});
 text(s,'R напрямую погашено 0. F: выделено24, выдано24, невыдано0 — модельная граница.\nПервый запуск G в m7–15 показан отдельно в XLSX. Это не фактический ledger банка.',64,597,1150,45,19,false,C.muted);break;}
 }
}
const partial=process.env.DECK_PARTIAL==='1';
const selectedSlides=partial?p.slides.items.slice(0,5):p.slides.items;
for(const [i,s] of selectedSlides.entries()){
 const b=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await b.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(build,'candidate.pptx'));
await fs.writeFile(path.join(build,'deck-state.json'),JSON.stringify({count:p.slides.items.length,main:8},null,2));
if(process.env.DECK_FINAL==='1'){
 const {pathToFileURL}=await import('node:url');
 const SKILL='/Users/davatoros/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
 const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
 const stem='CupMoscow2026-ОТП-'+(summary.team?.filename||'НазваниеКоманды');
 const finalRevision=path.join(build,'final-v2',stem+'.pptx');
 await fs.mkdir(path.dirname(finalRevision),{recursive:true});
 await finalizePresentation({workspaceDir:root,candidatePath:path.join(build,'candidate.pptx'),finalPath:finalRevision,pythonExecutable:'/Users/davatoros/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[3,4,5,6,...tableSlides].flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:p.slides.items.length,requiredNativeTableOwnerSlides:[3,4,5,6,...tableSlides],requiredNativeChartOwnerSlides:[2],fontPolicy:{basis:'design',families:['Arial']},materializeLiteralChartWorkbooks:true,verifyArtifactToolImport:true,receiptPath:path.join(root,'analysis/preparation/iteration-008-finalization-v2.json')});
 await fs.copyFile(finalRevision,path.join(out,stem+'.pptx'));
 const {execFile}=await import('node:child_process');const {promisify}=await import('node:util');
 await fs.mkdir('/private/tmp/otp008-cache',{recursive:true});
 await promisify(execFile)('/Users/davatoros/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice',['-env:UserInstallation=file:///private/tmp/otp008-lo','--headless','--convert-to','pdf','--outdir',out,path.join(out,stem+'.pptx')],{env:{...process.env,XDG_CACHE_HOME:'/private/tmp/otp008-cache'},maxBuffer:2000000});
}
console.log(`Built ${p.slides.items.length} slides; main8; final=${process.env.DECK_FINAL==='1'}`);
