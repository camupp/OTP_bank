import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root='/Users/davatoros/Desktop/OTP_bank';
const dir=path.join(root,'deliverables/iteration-008');
const build=path.join(dir,'.build');
const data=JSON.parse(await fs.readFile(path.join(build,'finance-inputs.json'),'utf8'));
const wb=Workbook.create();
const names=['Итог','Допущения','M05_год','Операции_39','Функции_39','Ручной_39','Запуск_39','Чувствительность'];
const sh=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const color={ink:'#14392F',green:'#006B45',light:'#EDF4EF',blue:'#1852A0',muted:'#64756D',amber:'#FFF2CC',red:'#A63D2F'};
const fmt='#,##0;(#,##0);"–"';
const dec='#,##0.0;(#,##0.0);"–"';
const diff='0.00;(0.00);0.00';
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const cell=(s,a,v)=>s.getRange(a).values=[[v]];
const formula=(s,a,f)=>{s.getRange(a).formulas=[[f]];s.getRange(a).format.font.color=f.includes('!')?color.green:'#17291F';};
const labels=(s,row,values,start='C')=>s.getRange(`${start}${row}`).write([values]);
const width=(s,c,px)=>s.getRange(`${c}1:${c}90`).format.columnWidthPx=px;
function init(s,title,last='S',rows=85){
 const r=s.getRange(`C1:${last}${rows}`);r.format.font={name:'Arial',size:11,color:'#17291F'};r.format.rowHeight=23;r.format.verticalAlignment='center';
 s.showGridLines=false;width(s,'A',14);width(s,'B',12);width(s,'C',415);
 for(let c=3;c<=18;c++)width(s,col(c),135);
 cell(s,'C2',title);s.getRange('C2').format.font={name:'Arial',size:16,bold:true,color:color.ink};s.getRange('C2:F2').format.rowHeight=32;
 s.getRange(`C4:${last}4`).format.borders={bottom:{style:'thin',color:'#CCD9D0'}};
}
function header(s,range){const r=s.getRange(range);r.format={fill:color.ink,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:38,verticalAlignment:'center',horizontalAlignment:'center',wrapText:true};}
function band(s,range){s.getRange(range).format={fill:color.light,font:{name:'Arial',size:11,bold:true,color:color.ink}};}
function note(s,a,t){cell(s,a,t);s.getRange(a).format.font={name:'Arial',size:11,italic:true,color:color.muted};}
function numeric(s,range,format=fmt){s.getRange(range).format.numberFormat=format;s.getRange(range).format.horizontalAlignment='right';}
const refs={money:'M05: iteration-007/rounds/003/supporting/finance-basis/annual-three-year.csv; EXPECTED/fixed96/E24, годы1–3.',
 resource:'CON-025: incumbent/monthly-resource.csv; EXPECTED/fixed96/QA100/×1/замещение0, m1–39.',
 launch:'CON-025: iteration-007/incumbent/first-launch.csv; E24, полный all-success календарь m1–39.',
 current:'Iteration-008: независимые checks/finance/check.py и delivery-summary.json; версии CON-026@v2 / CON-027@v2.'};

// One control area. The M05 source parameters are fixed context, not a new scenario engine.
{
 const s=sh['Допущения'];init(s,'Допущения, источники и изменяемые операции','H',68);width(s,'C',390);width(s,'D',125);width(s,'E',200);width(s,'F',22);width(s,'G',600);width(s,'H',25);
 note(s,'C3','Серые поля фиксируют проверенный M05. Синие поля меняют только операционные расчёты.');
 labels(s,5,['Параметр','Значение','Статус']);header(s,'C5:E5');cell(s,'G5','Источник и точное место');header(s,'G5:G5');
 const fixed=[
 [6,'Закупочный бюджет, минимум, руб./год',30000000,'Факт кейса','Кейс ОТП, физ.с.19. Обслуживание и доработки отдельно.'],
 [7,'Закупочный бюджет, максимум, руб./год',34000000,'Факт кейса','Кейс ОТП, физ.с.19.'],
 [8,'R в C, C за один R',1,'Факт кейса','Кейс ОТП, физ.с.10. Обратной конвертации нет.'],
 [9,'Расчётная совокупность, человек',7200,'Допущение M05',refs.money],
 [10,'Гарантия, R один раз в12месяцев',2500,'Правило проекта','CON-025/cards.md: оба подходящих квартала одного фиксированного окна.'],
 [11,'Весь будущий блок признания, R/год',24000000,'Допущение M05','18млнG+4,32млнtop+1,68млнspecial. Не поверх старого будущего R-фонда.'],
 [12,'Корпоративные события, C/год',96000000,'Допущение M05','Ставки событий сохраняются. Частота событий96млнC неизвестна в банке.'],
 [13,'Старый личный C в начале',160000000,'Допущение M05',refs.money],
 [14,'Старый личный R в начале',40000000,'Допущение M05',refs.money],
 [15,'Погашение перенесённых прав, за год',0.2,'Допущение M05','Старые остатки сохраняются. Не100% погашение; фактический backing неизвестен.'],
 [16,'Использование новых corporate C',0.6,'Допущение M05',refs.money],
 [17,'Использование нового R',1,'Допущение M05',refs.money],
 [18,'Цена модельного сертификата, C',2500,'Проектный SKU','Не установленный ценник реального каталога ОТП.'],
 [19,'Номинал модельного сертификата, руб.',500,'Проектный SKU','Не наличные и не фиксированный рублёвый курс валюты.'],
 [20,'Смешанная корзина, руб./C',0.194,'Допущение M05','Корзина5000C:80%сертификаты,20%мерч,с доставкой970руб.'],
 [21,'Новые R в сертификатах, руб./C',0.2,'Чувствительность','500руб./2500C. Поправка против0,194 составляет144тыс.руб./год.'],
 [22,'Годовой закупочный буфер, руб.',500000,'Допущение M05',refs.money],
 [23,'Непроведённые права U в старом сценарии, R',0,'Допущение M05','Реальные U неизвестны. Модельный0 не подтверждает их отсутствие.']
 ];
 for(const [r,label,value,status,source]of fixed){labels(s,r,[label,value,status]);cell(s,`G${r}`,source);s.getRange(`C${r}:E${r}`).format.fill='#F4F6F4';s.getRange(`G${r}`).format.wrapText=true;s.getRange(`C${r}:G${r}`).format.rowHeight=r===11||r===20?51:38;}
 const ops=[
 [25,'HR, руб./ч',1000,'Сценарная ставка'],[26,'Владелец / QA, руб./ч',1500,'Сценарная ставка'],[27,'Сотрудник, руб./ч',1000,'Сценарная ставка'],[28,'IT, руб./ч',2000,'Сценарная ставка'],
 [31,'Размер оплачиваемого блока, ч',20,'Операционный ввод'],[32,'Выпуск партии оператором, HRч/мес.',2,'Операционный ввод'],[33,'Независимая квитанция, HRч/мес.',2,'Операционный ввод'],[34,'Поддержка функций, ITч/мес.',8,'Операционный ввод'],[35,'Ручной ввод строки, мин.',2,'Операционный ввод'],[36,'Независимая сверка строки, мин.',1,'Операционный ввод'],[37,'Особые награды, строк/месяц',32,'Фиксированный максимум'],[38,'Доля ручных исключений q',0.1,'Операционный ввод B'],[39,'Пул ручного ввода, блоков/мес.',6,'Конечная мощность'],[40,'Пул ручной сверки, блоков/мес.',3,'Конечная мощность'],[41,'Горизонт операций, месяцев',39,'Фиксированный горизонт'],[43,'HR: максимум новых блоков',6,'Конечная мощность'],[44,'Owner/QA: максимум блоков',240,'Конечная мощность'],[45,'Сотрудники: максимум блоков',4,'Конечная мощность'],[46,'IT: максимум блоков',3,'Конечная мощность']
 ];
 for(const[r,label,value,status]of ops){labels(s,r,[label,value,status]);cell(s,`G${r}`,r<31?'Ставки прежней модели, не тарифы банка.':refs.current);s.getRange(`D${r}`).format.font.color=color.blue;s.getRange(`D${r}`).format.fill=color.amber;}
 for(const r of [15,16,17])numeric(s,`D${r}`,'0.0%');numeric(s,'D6:D14');numeric(s,'D18:D23');numeric(s,'D25:D46',dec);numeric(s,'D38','0.0%');numeric(s,'D25:D28');
 for(const r of [31,37,39,40,41,43,44,45,46])numeric(s,`D${r}`);
 for(const [r] of ops)if(r>=31)cell(s,`G${r}`,'');cell(s,'G31','CON-026@v2 / CON-027@v2: operations.csv и assumptions.csv; независимая проверка008.');cell(s,'G38','CON-027@v2: q — гипотеза доли исключений, проверяется в тени.');
 for(const r of [31,37,41]){s.getRange(`D${r}`).format.fill='#F4F6F4';s.getRange(`D${r}`).format.font.color='#17291F';}cell(s,'E31','Фиксированная единица');
 s.getRange('D20:D21').format.numberFormat='0.000';
 note(s,'C49','Изменение N, E24, частоты C, погашения или цен требует нового расчёта исходного M05.');
 note(s,'C51','Операционные формулы меняют часы, ставки, блоки, q и ручной режим. Сохранённая M05 не пересчитывается скрыто.');
 s.getRange('C49:H52').format.wrapText=false;s.getRange('C49:H52').format.rowHeight=28;
 s.dataValidations.add({range:'D38',rule:{type:'decimal',operator:'between',formula1:0,formula2:1}});
 s.dataValidations.add({range:'D31',rule:{type:'whole',operator:'between',formula1:1,formula2:160}});
 s.tabColor='#77A58B';s.freezePanes.freezeRows(5);
}

// Annual M05 source rows plus live, readable bridges and stock-flow equations.
{
 const s=sh['M05_год'];init(s,'Сохранённый M05: годовые потоки и обеспечение','J',54);width(s,'C',405);for(const c of ['D','E','F'])width(s,c,150);width(s,'G',24);width(s,'H',610);
 note(s,'C3','Фиксированный проверенный вход. Полный годовой E24-предел, а не выплаты первого года запуска.');
 labels(s,6,['Показатель, C/R или руб.','Год1','Год2','Год3']);header(s,'C6:F6');
 const labelsByRow={8:'Личный C на начало',9:'Личный R на начало',10:'Новые corporate C',11:'Новый R после разрешения',12:'Конвертация R в C',13:'Погашение C',14:'Прямое погашение R',15:'Личный C на конец',16:'Личный R на конец',17:'Все личные C+R на конец',20:'Невыданный F на начало',21:'Выделено F',22:'Выдано из F',23:'Не выдано / закрыто по правилу',24:'Невыданный F на конец',26:'Модельный U, не реальное отсутствие прав',28:'Закупочная касса, руб.',29:'Логистическая касса, руб.',30:'Общая касса наград, руб.',31:'Резерв на начало, руб.',32:'Резерв на конец, руб.',33:'Изменение резерва, руб.',34:'Буфер, руб.',35:'Обеспечение M05, руб.',36:'Поправка на новые сертификаты, руб.',37:'Обеспечение с сертификатами, руб.',38:'Закупочный лимит34млн, руб.',39:'Остаток лимита34млн, руб.',40:'Нижняя граница30млн, руб.',41:'Остаток относительно30млн, руб.',43:'Склад на начало, руб.',44:'Склад на конец по источнику, руб.',45:'Использовано из склада, руб.',46:'Склад на конец по равенству, руб.'};
 for(const[r,t]of Object.entries(labelsByRow))cell(s,`C${r}`,t);
 const src=data.summary.procurement_and_currency;
 for(let i=0;i<3;i++){
  const c=col(i+3),prev=col(i+2),r=src[i];
  for(const[row,key]of [[10,'fixed_C_issued'],[11,'R_posted'],[12,'R_to_C'],[13,'C_redeemed'],[14,'direct_R_redeemed'],[21,'F_granted'],[22,'F_posted'],[23,'F_unissued_expired'],[28,'procurement_cash_RUB'],[29,'logistics_cash_RUB'],[31,'reserve_open_RUB'],[32,'reserve_close_RUB']])cell(s,`${c}${row}`,r[key]);
  if(i===0){cell(s,`${c}8`,r.C_open);cell(s,`${c}9`,r.R_open);cell(s,`${c}20`,0);}else{formula(s,`${c}8`,`=${prev}15`);formula(s,`${c}9`,`=${prev}16`);formula(s,`${c}20`,`=${prev}24`);}
  formula(s,`${c}15`,`=${c}8+${c}10+${c}12-${c}13`);formula(s,`${c}16`,`=${c}9+${c}11-${c}12-${c}14`);formula(s,`${c}17`,`=SUM(${c}15:${c}16)`);formula(s,`${c}24`,`=${c}20+${c}21-${c}22-${c}23`);cell(s,`${c}26`,0);
  formula(s,`${c}30`,`=SUM(${c}28:${c}29)`);formula(s,`${c}33`,`=${c}32-${c}31`);formula(s,`${c}34`,"='Допущения'!$D$22");formula(s,`${c}35`,`=SUM(${c}30,${c}33:${c}34)`);formula(s,`${c}36`,"='Допущения'!$D$11*('Допущения'!$D$21-'Допущения'!$D$20)");formula(s,`${c}37`,`=SUM(${c}35:${c}36)`);formula(s,`${c}38`,"='Допущения'!$D$7");formula(s,`${c}39`,`=${c}38-${c}37`);formula(s,`${c}40`,"='Допущения'!$D$6");formula(s,`${c}41`,`=${c}40-${c}37`);
 }
 const inv=[{open:0,close:77600,used:23590400},{open:77600,close:120280,used:23528320},{open:120280,close:115624,used:23478656}];
 for(let i=0;i<3;i++){const c=col(i+3);cell(s,`${c}43`,inv[i].open);cell(s,`${c}44`,inv[i].close);cell(s,`${c}45`,inv[i].used);formula(s,`${c}46`,`=${c}43+${c}30-${c}45`);}
 numeric(s,'D8:F46');for(const r of [15,16,17,24,30,35,37,39,41,46])band(s,`C${r}:F${r}`);
 cell(s,'H8',refs.money);cell(s,'H12','Источники правил: кейс, физ.с.10–12. Личные C/R не сгорают. Конвертация1:1 сохраняет общую массу.');cell(s,'H20','Неизвестные реальные старые остатки, U и обеспечение не заменены утверждением о фактическом нуле. F — не личный R.');cell(s,'H28','31,684млн = касса+изменение резерва+буфер+сертификатная поправка, до комиссий. Резерв не вторая закупка.');cell(s,'H35','Область: EXPECTED/fixed96/old20/E24/базовые цены/34млн. Сценарные деньги не доказывают утверждённый бюджет банка.');cell(s,'H43','Закупка, доставка, потребление и изменение склада относятся к одному периоду. Склад не суммируется с резервом второй раз.');s.getRange('H8:H46').format.wrapText=true;
 for(const r of [8,12,20,28,35,43])s.getRange(`C${r}:H${r}`).format.rowHeight=45;
 s.getRange('D39:F41').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});
 s.freezePanes.freezeRows(6);
}

const baseBy=(m,role)=>data.base_monthly.find(r=>Number(r.month)===m&&r.role===role);
const launchBy=m=>data.launch.find(r=>Number(r.month)===m);
// Common saved calendar and the explicit physical batch release used by implementation A.
{
 const s=sh['Операции_39'];init(s,'Операции: сохранённая бронь и фактический выпуск','Q',70);for(let i=2;i<17;i++)width(s,col(i),i===2?66:126);
 note(s,'C3','Основная область:QA100/×1. Существующая работа не исчезает. Дополнительный выпуск:2+2HRч/мес.');note(s,'C5',refs.resource);
 labels(s,7,['Месяц','HR спрос, ч','База HR, ч','HR бронь, ч','Owner бронь, ч','Сотрудники бронь, ч','IT бронь, ч','База, руб.','HR с выпуском, ч','Бронь HR, ч','Новая касса, руб.','Пакет всего, руб.','Новый труд, руб.','','Очередь HR, ч']);header(s,'C7:Q7');s.getRange('C7:Q7').format.rowHeight=62;width(s,'P',22);s.getRange('P7').format.fill='#FFFFFF';
 for(let m=1;m<=39;m++){
  const r=m+7,h=baseBy(m,'HR'),o=baseBy(m,'owner_QA'),e=baseBy(m,'employee'),it=baseBy(m,'IT');labels(s,r,[m,h.demand_h,h.base_available_h,h.booked_h,o.booked_h,e.booked_h,it.booked_h]);
  formula(s,`J${r}`,`=IF(COUNT('Допущения'!$D$25:$D$28)=4,F${r}*'Допущения'!$D$25+G${r}*'Допущения'!$D$26+H${r}*'Допущения'!$D$27+I${r}*'Допущения'!$D$28,NA())`);
  formula(s,`K${r}`,`=D${r}+SUM('Допущения'!$D$32:$D$33)`);
  const queue=m===1?'0':`Q${r-1}`;
  formula(s,`L${r}`,`=MAX(F${r},MIN('Допущения'!$D$43*'Допущения'!$D$31,MAX(0,ROUNDUP((K${r}+${queue}-E${r})/'Допущения'!$D$31,0))*'Допущения'!$D$31))`);
  formula(s,`M${r}`,`=(L${r}-F${r})*'Допущения'!$D$25`);formula(s,`N${r}`,`=SUM(J${r},M${r})`);formula(s,`O${r}`,`=SUM('Допущения'!$D$32:$D$33)*'Допущения'!$D$25`);formula(s,`Q${r}`,`=MAX(0,${queue}+K${r}-E${r}-L${r})`);
 }
 cell(s,'C48','39мес.');for(const c of ['J','M','N','O'])formula(s,`${c}48`,`=SUM(${c}8:${c}46)`);formula(s,'Q48','=MAX(Q8:Q46)');band(s,'C48:Q48');numeric(s,'D8:Q48',dec);for(const c of ['J','M','N','O'])numeric(s,`${c}8:${c}48`);
 labels(s,51,['Настройка','Часы','Ставка, руб./ч','Стоимость, руб.']);header(s,'C51:F51');width(s,'C',90);
 const setup=[['HR',120,25],['Owner/QA',420,26],['IT',720,28],['Сотрудники',1800,27]];
 for(let i=0;i<4;i++){const r=52+i;labels(s,r,[setup[i][0],setup[i][1]]);formula(s,`E${r}`,`='Допущения'!D${setup[i][2]}`);formula(s,`F${r}`,`=D${r}*E${r}`);}cell(s,'C56','Итого');formula(s,'F56','=SUM(F52:F55)');band(s,'C56:F56');numeric(s,'D52:F56');
 labels(s,59,['Новая настройка функций','Часы','Ставка, руб./ч','Стоимость, руб.']);header(s,'C59:F59');const fresh=[['IT',320,28],['HR',16,25],['Owner/QA',24,26]];
 for(let i=0;i<3;i++){const r=60+i;labels(s,r,[fresh[i][0],fresh[i][1]]);formula(s,`E${r}`,`='Допущения'!D${fresh[i][2]}`);formula(s,`F${r}`,`=D${r}*E${r}`);}cell(s,'C63','Итого');formula(s,'F63','=SUM(F60:F62)');band(s,'C63:F63');numeric(s,'D60:F63');s.getRange('C59:F59').format.rowHeight=66;
 note(s,'H52','Setup3,990млн включает подготовку1,890 и полный теневой квартал/закрытие2,100млн.');note(s,'H54','Пакет использует252тыс. внутри прежнего setup. Никакая часть настройки не вычитается как экономия.');s.getRange('H52:Q55').format.wrapText=false;
 s.getRange('Q8:Q48').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0.00001,format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});s.freezePanes.freezeRows(7);s.freezePanes.freezeColumns(3);
}

// The same source calendar, replacing only structural checks for implementation B.
{
 const s=sh['Функции_39'];init(s,'Адресные функции: замена операций и бронь','T',56);for(let i=2;i<20;i++)width(s,col(i),i===2?68:126);
 cell(s,'C3','Доля q');formula(s,'D3',"=IF(ISNUMBER('Допущения'!D38),'Допущения'!D38,NA())");numeric(s,'D3','0.0%');note(s,'F3','Профессиональный QA и персональные4мин не заменяются функцией.');note(s,'C5',refs.current);
 labels(s,7,['Месяц','HR до, ч','Owner до, ч','Обычных записей','HR после, ч','Owner после, ч','IT после, ч','HR бронь, ч','Owner бронь, ч','IT бронь, ч','Сотрудники, ч','Условная касса, руб.','Консервативная касса, руб.','Новый труд, руб.','Очередь HR, ч','Очередь Owner, ч','Очередь IT, ч']);header(s,'C7:S7');s.getRange('C7:S7').format.rowHeight=66;
 for(let m=1;m<=39;m++){
  const r=m+7,h=baseBy(m,'HR'),o=baseBy(m,'owner_QA'),it=baseBy(m,'IT'),e=baseBy(m,'employee'),cal=launchBy(m);labels(s,r,[m,h.demand_h,o.demand_h,cal.ordinary_cycle_records]);
  formula(s,`G${r}`,`=D${r}-180*(8+4)/60+(6*(8+4)+180*$D$3*(8+4))/60+SUM('Допущения'!$D$32:$D$33)`);
  formula(s,`H${r}`,`=E${r}-(1-$D$3)*F${r}*1760/2400*2/60`);formula(s,`I${r}`,`=${it.demand_h}+'Допущения'!$D$34`);
  const qp=m===1?'0':`Q${r-1}`,rp=m===1?'0':`R${r-1}`,sp=m===1?'0':`S${r-1}`;
  formula(s,`J${r}`,`=MIN('Допущения'!$D$43*'Допущения'!$D$31,MAX(0,ROUNDUP((G${r}+${qp}-${h.base_available_h})/'Допущения'!$D$31,0))*'Допущения'!$D$31)`);
  formula(s,`K${r}`,`=MIN('Допущения'!$D$44*'Допущения'!$D$31,MAX(0,ROUNDUP((H${r}+${rp}-${o.base_available_h})/'Допущения'!$D$31,0))*'Допущения'!$D$31)`);
  formula(s,`L${r}`,`=MIN('Допущения'!$D$46*'Допущения'!$D$31,MAX(0,ROUNDUP((I${r}+${sp}-${it.base_available_h})/'Допущения'!$D$31,0))*'Допущения'!$D$31)`);cell(s,`M${r}`,e.booked_h);
  formula(s,`N${r}`,`=IF(COUNT('Допущения'!$D$25:$D$28)=4,J${r}*'Допущения'!$D$25+K${r}*'Допущения'!$D$26+L${r}*'Допущения'!$D$28+M${r}*'Допущения'!$D$27,NA())`);
  formula(s,`O${r}`,`='Операции_39'!N${r}+MAX(0,L${r}-${it.booked_h})*'Допущения'!$D$28`);
  formula(s,`P${r}`,`=SUM('Допущения'!$D$32:$D$33)*'Допущения'!$D$25+'Допущения'!$D$34*'Допущения'!$D$28`);
  formula(s,`Q${r}`,`=MAX(0,${qp}+G${r}-${h.base_available_h}-J${r})`);formula(s,`R${r}`,`=MAX(0,${rp}+H${r}-${o.base_available_h}-K${r})`);formula(s,`S${r}`,`=MAX(0,${sp}+I${r}-${it.base_available_h}-L${r})`);
 }
 cell(s,'C48','39мес.');for(const c of ['N','O','P'])formula(s,`${c}48`,`=SUM(${c}8:${c}46)`);for(const c of ['Q','R','S'])formula(s,`${c}48`,`=MAX(${c}8:${c}46)`);band(s,'C48:S48');numeric(s,'D8:S48',dec);numeric(s,'F8:F46');numeric(s,'N8:P48');
 note(s,'C51','Условную бронь нельзя высвободить до тени и оплаченного fallback. Консервативная касса сохраняет полный ручной контроль.');note(s,'C53','Синяя q — гипотеза доли исключений, не измеренная доля ошибок банка. Пилот120человек не доказывает q для7200.');s.getRange('C51:S54').format.wrapText=false;s.getRange('Q8:S48').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0.00001,format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});s.freezePanes.freezeRows(7);s.freezePanes.freezeColumns(3);
}

// Explicit per-row manual fallback. Required blocks and finite pools are both visible.
{
 const s=sh['Ручной_39'];init(s,'Ручной ввод и независимая сверка при отсутствии batch','P',55);for(let i=2;i<16;i++)width(s,col(i),i===2?75:140);
 note(s,'C3','Цена полного39месячного ручного режима. Дополнительные пулы, без скрытого свободного времени прежнегоHR.');note(s,'C5',refs.launch);
 labels(s,7,['Месяц','Обычных записей','Гарантия, R','Special, строк','Всего строк','Ввод, ч','Сверка, ч','Ввод, блоки','Сверка, блоки','Требуется, руб.','Простой, ч','Мощность']);header(s,'C7:N7');s.getRange('C7:N7').format.rowHeight=58;
 for(let m=1;m<=39;m++){
  const r=m+7,cal=launchBy(m);labels(s,r,[m,cal.ordinary_cycle_records,cal.guarantee_post_all_success_R]);formula(s,`F${r}`,"='Допущения'!$D$37");formula(s,`G${r}`,`=D${r}+E${r}/'Допущения'!$D$10+F${r}`);formula(s,`H${r}`,`=G${r}*'Допущения'!$D$35/60`);formula(s,`I${r}`,`=G${r}*'Допущения'!$D$36/60`);formula(s,`J${r}`,`=ROUNDUP(H${r}/'Допущения'!$D$31,0)`);formula(s,`K${r}`,`=ROUNDUP(I${r}/'Допущения'!$D$31,0)`);formula(s,`L${r}`,`=SUM(J${r}:K${r})*'Допущения'!$D$31*'Допущения'!$D$25`);formula(s,`M${r}`,`=SUM(J${r}:K${r})*'Допущения'!$D$31-SUM(H${r}:I${r})`);formula(s,`N${r}`,`=IF(AND(J${r}<='Допущения'!$D$39,K${r}<='Допущения'!$D$40),"вместимо","нужен ресурс")`);
 }
 cell(s,'C48','39мес.');formula(s,'L48','=SUM(L8:L46)');formula(s,'G48','=MAX(G8:G46)');formula(s,'J48','=MAX(J8:J46)');formula(s,'K48','=MAX(K8:K46)');band(s,'C48:N48');numeric(s,'D8:M48',dec);for(const c of ['D','E','F','G','J','K','L'])numeric(s,`${c}8:${c}48`);
 s.getRange('N8:N46').conditionalFormats.add('containsText',{text:'нужен',format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});
 note(s,'C51','Двойные минуты2→4 и1→2 требуют пиков11+6блоков вместо6+3. Это потребность, не обеспеченная мощность.');note(s,'C53','Обычные строки — верхняя граница всех персональных top при массовой ничьей. Повторные команды не новые выдачи.');s.getRange('C51:P54').format.wrapText=false;s.freezePanes.freezeRows(7);s.freezePanes.freezeColumns(3);
}

// Launch calendar is kept apart from the full annual E24 funding model.
{
 const s=sh['Запуск_39'];init(s,'Первый запуск:9когорт и первая гарантияm7–15','N',72);width(s,'C',90);for(const c of ['D','E','F','G','H'])width(s,c,150);width(s,'I',24);width(s,'J',195);width(s,'K',165);width(s,'L',165);width(s,'M',165);width(s,'N',165);
 note(s,'C3','Верхний all-success сценарий. Проводка возможна только после независимого разрешения, затем ещё нужны заказ и получение.');
 labels(s,7,['Месяц','Обычных записей','G, R','Top, R','Special, R','Всего R']);header(s,'C7:H7');
 for(let m=1;m<=39;m++){const r=m+7,cal=launchBy(m);labels(s,r,[m,cal.ordinary_cycle_records,cal.guarantee_post_all_success_R,cal.top_full_all_success_R,cal.special_full_R]);formula(s,`H${r}`,`=SUM(E${r}:G${r})`);}
 cell(s,'C48','39мес.');for(const c of ['E','F','G','H'])formula(s,`${c}48`,`=SUM(${c}8:${c}46)`);band(s,'C48:H48');numeric(s,'D8:H48');
 labels(s,7,['Когорта','Человек','Старт окна,m','ПерваяG,m','СуммаG,R'],'J');header(s,'J7:N7');
 for(let i=1;i<=9;i++){const r=i+7;labels(s,r,[i,800,i],'J');formula(s,`M${r}`,`=L${r}+6`);formula(s,`N${r}`,`=K${r}*'Допущения'!$D$10`);}cell(s,'J18','Все9когорт');formula(s,'K18','=SUM(K8:K16)');formula(s,'N18','=SUM(N8:N16)');band(s,'J18:N18');numeric(s,'J8:N18');
 labels(s,22,['Период','G, R','Top, R','Special, R','Всего R'],'J');header(s,'J22:N22');
 for(let i=0;i<4;i++){const r=23+i,lo=i*12+8,hi=Math.min(lo+11,46);cell(s,`J${r}`,i===3?'m37–39':`Год${i+1}`);for(let k=0;k<4;k++)formula(s,`${col(10+k)}${r}`,`=SUM(${col(4+k)}${lo}:${col(4+k)}${hi})`);}numeric(s,'K23:N26');
 note(s,'J30','ОдинG2500R за оба подходящих квартала одного окна раз в12месяцев. Это не две выплаты в год.');note(s,'J35','У позднего новичка ожидание может достигать15месяцев. Неудачное окно: новая возможность через год.');note(s,'J40','7200 — финансовый сценарий. Тень:120человек трёх семейств и отдельный вычислительный replay масштаба7200.');s.getRange('J30:N44').format.wrapText=false;s.getRange('J30:N44').format.rowHeight=26;
 cell(s,'C51',refs.launch);cell(s,'C53','m1 начинается после подготовки, полного теневого квартала и обеспеченного закрытия. Сроки относительные, не календарь банка.');s.getRange('C51:N55').format.wrapText=false;s.freezePanes.freezeRows(7);
}

// Primary outputs read completed builds. Checks never feed these outputs.
{
 const s=sh['Итог'];init(s,'ОТП Мания. Финансовая модель','O',44);width(s,'C',450);for(const c of ['D','E','F'])width(s,c,160);width(s,'G',24);for(const c of ['H','I','J','K','L','M','N','O'])width(s,c,100);
 note(s,'C3','Проектный сценарий, не утверждённый бюджет банка. Закупка отдельно от операционной стоимости.');
 labels(s,5,['Обеспечение наград, руб.','Год1','Год2','Год3']);header(s,'C5:F5');
 const rows=[[7,'Касса наград',30],[8,'Изменение резерва',33],[9,'Буфер',34],[10,'Сертификатная поправка',36],[11,'Требуется до комиссий',37],[12,'Закупочный лимит',38],[13,'Остаток лимита',39]];
 for(const[r,label,src]of rows){cell(s,`C${r}`,label);for(let i=0;i<3;i++)formula(s,`${col(3+i)}${r}`,`='M05_год'!${col(3+i)}${src}`);}numeric(s,'D7:F13');band(s,'C11:F11');
 labels(s,17,['Операции и настройка, руб.','Контроль без адаптации','Пакет отчётов','Функции портала']);header(s,'C17:F17');s.getRange('C17:F17').format.rowHeight=50;
 const labelsOut={18:'Настройка механики',19:'Дополнительная настройка внедрения',20:'Консервативная бронь за39месяцев',21:'Настройка+39месяцев',23:'Новая деятельность за12месяцев',24:'Дополнительная касса вгод1',25:'Полный ручной режим с настройкой'};for(const[r,label]of Object.entries(labelsOut))cell(s,`C${r}`,label);
 for(const c of ['D','E','F'])formula(s,`${c}18`,"='Операции_39'!F56");cell(s,'D19',0);cell(s,'E19',0);formula(s,'F19',"='Операции_39'!F63");formula(s,'D20',"='Операции_39'!J48");formula(s,'E20',"='Операции_39'!N48");formula(s,'F20',"='Функции_39'!O48");for(const c of ['D','E','F'])formula(s,`${c}21`,`=SUM(${c}18:${c}20)`);cell(s,'D23','не добавлена');formula(s,'E23',"=SUM('Операции_39'!O8:O19)");formula(s,'F23',"=SUM('Функции_39'!P8:P19)");cell(s,'D24',0);formula(s,'E24',"=SUM('Операции_39'!M8:M19)");formula(s,'F24',"=SUM('Функции_39'!O8:O19)-SUM('Операции_39'!J8:J19)");cell(s,'D25','не проработан');formula(s,'E25',"=E21+'Ручной_39'!L48");formula(s,'F25',"=F21+'Ручной_39'!L48");numeric(s,'D18:F25');band(s,'C21:F21');
 note(s,'C28','Контроль не включает новый фактический выпуск/fallback.156тыс. деятельности пакета отличаются от180тыс. новой брони.');
 note(s,'C30','Для функций условная q10бронь16,380млн и setup21,062млн не высвобождают деньги до подтверждённой тени и оплаченногоfallback.');
 note(s,'C32','Годовой M05 обеспечивает весь E24-предел. Первый запуск выплат показан отдельно:9когорт,первыеGm7–15.');
 note(s,'C34','Реальные остатки/непроведённые права,частотаC,цены/комиссии/SKU,люди и ежедневная мощность требуют проверки до обещаний.');
 s.getRange('C28:O35').format.wrapText=false;s.getRange('C28:O35').format.rowHeight=25;
 labels(s,38,['Проектный год','Требуется, руб.','Лимит, руб.'],'H');for(let i=0;i<3;i++){const r=39+i;cell(s,`H${r}`,`Год${i+1}`);formula(s,`I${r}`,`=${col(i+3)}11`);formula(s,`J${r}`,`=${col(i+3)}12`);}numeric(s,'I39:J41');
 const chart=s.charts.add('line',s.getRange('H38:J41'));chart.setPosition('H5','O15');chart.title='Обеспечение наград, млн руб.';chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=14;chart.legend={position:'top',textStyle:{typeface:'Arial',fontSize:11}};chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};chart.yAxis={numberFormatCode:'0.0,,',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};chart.series.items[0].line={fill:color.green,style:'solid',width:2};chart.series.items[1].line={fill:'#85938B',style:'dashed',width:2};
 cell(s,'H18','Текущие операционные вводы');s.getRange('H18').format.font.bold=true;cell(s,'H20','Доля исключений q');formula(s,'L20',"='Функции_39'!D3");numeric(s,'L20','0.0%');cell(s,'H22','Максимальная очередь, ч');formula(s,'L22',"=MAX('Операции_39'!Q48,'Функции_39'!Q48:S48)");numeric(s,'L22',dec);cell(s,'H24','Ручной режим при отказе');formula(s,'L24',"=IF(AND('Ручной_39'!J48<='Допущения'!D39,'Ручной_39'!K48<='Допущения'!D40),\"вместимо\",\"нужен ресурс\")");s.getRange('L22').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:.00001,format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});s.getRange('L24').conditionalFormats.add('containsText',{text:'нужен',format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});note(s,'H26','Сценарная вместимость не подтверждает реальных людей или дневной SLA.');
 s.getRange('C7:F25').format.font.color=color.ink;header(s,'C17:F17');s.getRange('C17:F17').format.rowHeight=50;s.getRange('D13:F13').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});s.tabColor=color.ink;
}

// Saved sensitivities and terminal reconciliations. No output formula reads this sheet.
{
 const s=sh['Чувствительность'];init(s,'Сохранённые ограничения и независимые сверки','K',56);width(s,'C',470);width(s,'D',180);width(s,'E',145);width(s,'F',170);width(s,'G',24);width(s,'H',590);
 note(s,'C3','Это сохранённые результаты M05 и ограничения,не новая динамическая большая сетка. Изменённые операции рассчитываются на своих листах.');
 labels(s,6,['Сохранённый сценарий, год1','Требуется, руб.','Лимит, руб.','Итог']);header(s,'C6:F6');
 const sources=data.preserved_budget_sensitivity;
 const picks=[['База с сертификатами','EXPECTED',96000000,24000000],['Больше корпоративныхC:144млн','EXPECTED',144000000,24000000],['Конверт E36','EXPECTED',96000000,36000000],['Все новые и старое35%','FULL_NEW_OLD35',96000000,24000000],['Все новые и цены+20%','FULL_NEW_PRICE20',96000000,24000000]];
 for(let i=0;i<picks.length;i++){const r=8+i,[label,scenario,fixed,env]=picks[i],x=sources.find(t=>t.scenario===scenario&&Number(t.fixed_C_year)===fixed&&Number(t.E_R_year)===env&&Number(t.year)===1);labels(s,r,[label,Number(x.certificate500_funding_RUB),34000000]);formula(s,`F${r}`,`=IF(D${r}<=E${r},"проходит область","не проходит")`);}numeric(s,'D8:E12');
 cell(s,'H8','Источник: сохранённый budget.csv независимой проверки007. База:31,684млн доfees. 30млн вгод1 не проходят.');cell(s,'H13','QA50/0 сохраняют полный дополнительный независимый QA. Для функций:110,610/208,530млн условной брони39месяцев,не дешёвый запуск.');cell(s,'H18','Рост исключений ещё120апелляций+72исправления+12инцидентов:77,6ч/мес,99,8тыс. деятельности/мес. Касса/люди отдельно.');cell(s,'H23','Ручные минуты×2 требуют11+6блоков вместо6+3. Исходная конечная мощность не проходит. Права и резервы сохраняются.');s.getRange('H8:H26').format.wrapText=true;
 labels(s,16,['Сверка при исходных операционных вводах','Разница / очередь','Допуск']);header(s,'C16:E16');
 const ctr=[
 [18,'Год1 обеспечение с сертификатами',"='M05_год'!D37-31684000"],[19,'Год2 обеспечение с сертификатами',"='M05_год'!E37-30132000"],[20,'Год3 обеспечение с сертификатами',"='M05_год'!F37-28890400"],
 [22,'Личный C конец, год1',"='M05_год'!D15-166400000"],[23,'Личный R конец, год1',"='M05_год'!D16-32000000"],[24,'Склад конец, год1',"='M05_год'!D46-'M05_год'!D44"],
 [26,'Setup основной',"='Операции_39'!F56-3990000"],[27,'Setup функций дополнительный',"='Операции_39'!F63-692000"],[28,'База брони39месяцев',"='Операции_39'!J48-19320000"],[29,'Пакет,бронь39месяцев',"='Операции_39'!N48-19500000"],[30,'Условные функции q10',"='Функции_39'!N48-16380000"],[31,'Консервативные функции',"='Функции_39'!O48-19500000"],[32,'Ручной режим39месяцев',"='Ручной_39'!L48-6060000"],[34,'Пакет:максимальная очередь,ч',"='Операции_39'!Q48"],[35,'Функции:максимальная очередьHR,ч',"='Функции_39'!Q48"],[36,'Функции:максимальная очередьOwner,ч',"='Функции_39'!R48"],[37,'Функции:максимальная очередьIT,ч',"='Функции_39'!S48"],[39,'Первые9когорт:людей',"='Запуск_39'!K18-7200"],[40,'Первые9когорт:G,R',"='Запуск_39'!N18-18000000"]];
 for(const[r,label,f]of ctr){cell(s,`C${r}`,label);formula(s,`D${r}`,f);cell(s,`E${r}`,0.01);}numeric(s,'D18:E40',diff);s.getRange('D18:D40').format.font.color='#17291F';s.getRange('D18:D40').conditionalFormats.addCustom('ABS(D18)>0.01',{fill:'#FCE8E6',font:{color:color.red,bold:true}});s.getRange('F8:F12').conditionalFormats.add('containsText',{text:'не проходит',format:{fill:'#FCE8E6',font:{color:color.red,bold:true}}});
 for(const r of [8,13,18,23])s.getRange(`C${r}:H${r}`).format.rowHeight=48;
 note(s,'C44','При изменении операционных вводов разница с сохранённым контролем ожидаемо изменится. Это сверка,а не вход расчёта.');note(s,'C46','Реальные закупки,финансирование,люди,ledger и мотивационный эффект не доказаны этим файлом.');s.getRange('C44:K48').format.wrapText=false;s.freezePanes.freezeRows(6);
}

// Meaningful calculation checks, then a reversible input change and missing-input check.
wb.recalculate();
const tests=[];
const value=(sheet,address)=>sh[sheet].getRange(address).values[0][0];
function eq(label,actual,expected,tol=.02){const pass=typeof actual==='number'&&Math.abs(actual-expected)<=tol;tests.push({label,actual,expected,pass});if(!pass)throw new Error(`${label}: ${actual} != ${expected}`);}
eq('M05 year1',value('M05_год','D37'),31684000);eq('A39 bookings',value('Операции_39','N48'),19500000);eq('B q10 bookings',value('Функции_39','N48'),16380000);eq('B conservative',value('Функции_39','O48'),19500000);eq('manual39',value('Ручной_39','L48'),6060000);eq('A total setup39',value('Итог','E21'),23490000);eq('B conservative setup39',value('Итог','F21'),24182000);eq('A new activity12',value('Итог','E23'),48000);eq('B new activity12',value('Итог','F23'),240000);eq('G first cohort month',value('Запуск_39','M8'),7);eq('G ninth cohort month',value('Запуск_39','M16'),15);
cell(sh['Допущения'],'D38',.3);wb.recalculate();eq('B q30 recalculates',value('Функции_39','N48'),16860000);cell(sh['Допущения'],'D38',null);wb.recalculate();const missing=value('Функции_39','D3');tests.push({label:'blank q remains unavailable',actual:missing,pass:typeof missing!=='number'});if(typeof missing==='number')throw new Error('Missing q became zero');cell(sh['Допущения'],'D38',0);wb.recalculate();eq('zero q remains legitimate',value('Функции_39','D3'),0);cell(sh['Допущения'],'D38',.1);
cell(sh['Допущения'],'D35',4);cell(sh['Допущения'],'D36',2);wb.recalculate();eq('double input requires11blocks',value('Ручной_39','J48'),11);eq('double receipt requires6blocks',value('Ручной_39','K48'),6);const resourceState=value('Итог','L24');tests.push({label:'double minutes expose resource need in summary',actual:resourceState,pass:resourceState==='нужен ресурс'});if(resourceState!=='нужен ресурс')throw new Error('Summary lost manual capacity failure');cell(sh['Допущения'],'D35',2);cell(sh['Допущения'],'D36',1);wb.recalculate();eq('restored manual39',value('Ручной_39','L48'),6060000);
const errorScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan',maxChars:8000});
const inspect=await wb.inspect({kind:'table',range:'Итог!C17:F25',include:'values,formulas',tableMaxRows:10,tableMaxCols:4,maxChars:5000});
await fs.writeFile(path.join(build,'workbook-checks.json'),JSON.stringify({tests,errorScan:errorScan.ndjson,inspection:inspect.ndjson,engine:'Artifact Tool recalculation; native Excel UI not exercised',source_scope:'Saved M05 inputs, live bridges and changed operating calculations',sheets:names},null,2));
const previews={Итог:'C1:O35',Допущения:'C1:H52',M05_год:'C1:H48',Операции_39:'C1:Q20',Функции_39:'C1:S20',Ручной_39:'C1:N20',Запуск_39:'C1:N53',Чувствительность:'C1:K46'};
for(const name of names){const png=await wb.render({sheetName:name,range:previews[name],scale:1.3,format:'png'});await fs.writeFile(path.join(build,`workbook-preview-${name}.png`),new Uint8Array(await png.arrayBuffer()));}
const setupPreview=await wb.render({sheetName:'Операции_39',range:'C48:Q64',scale:1.3,format:'png'});await fs.writeFile(path.join(build,'workbook-preview-настройка.png'),new Uint8Array(await setupPreview.arrayBuffer()));
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(dir,'CupMoscow2026-ОТП-НазваниеКоманды.xlsx'));
console.log(JSON.stringify({exported:'CupMoscow2026-ОТП-НазваниеКоманды.xlsx',sheets:names.length,tests:tests.length,errorScan:errorScan.ndjson},null,2));
