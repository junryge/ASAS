from pathlib import Path
import json,html,csv,hashlib
P=Path(__file__).resolve().parent;C=json.loads((P/'rule_config.json').read_text());E=html.escape
FABS=['M14A','M14B','M16A','M16B','M16HUB'];prefix={'M14A':'M14',**{f:f for f in FABS[1:]}}
D=list(csv.DictReader((P/'source_dictionary.csv').open(encoding='utf-8-sig')))
SCOPE={'M14A':'M14A · 3F / CSV의 M14는 M14A 전용','M14B':'M14B · 7F / 4ALF 층간 리프터·4ABLD HUB 연결','M16A':'M16A MCS · 2F·3F·6F / Queue는 HUB 3F도 포함','M16B':'M16B · 10F / HUB 반송은 M16A 6F 경유','M16HUB':'HUBROOM · M16 3F / M14HUB·Bridge와 같은 영역'}
NOTES={'M14A':'남·북 CNV의 시간과 물량을 같은 방향끼리 확인합니다. 4AFC3201은 남측, 4AFC3301은 북측입니다. 장비 ID를 방향 표기보다 우선합니다.','M14B':'4분 초과율은 현재 설정에서 비활성입니다. 반송 지연 룰에는 완료 반송시간을 사용합니다. M14A↔B 연결 4ALF와 HUB 연결 4ABLD의 PIO는 측정 출발 영역에 귀속합니다.','M16A':'전체 MCS Queue를 6F만의 위험으로 해석하지 않습니다. 대기 기여에 추가 확인 계수를 적용합니다. 8/26 STOP 작업은 사건 설명이며 점수 입력이 아닙니다.','M16B':'M16A와 연결되는 층간 경로를 확인합니다. 일반 Sorter와 CU Sorter는 별개 장비입니다. 이번 버전은 일반 Sorter만 평가하고 모든 FAB의 CU Sorter는 미평가입니다.','M16HUB':'평소 비우는 임시 대기 공간입니다. 저장 후 MCS가 1분마다 재반송 가능 상태를 확인합니다. Reserved 포함 저장률의 지속·해소와 실제 반송 영향을 함께 봅니다. HUB에는 STK와 Sorter가 없습니다.'}
RULES={'delay':('R001','반송 지연 지속',45),'backlog':('R002','미완료 물량 누적',40),'completion':('R003','처리 감소와 대기 증가',85),'port':('R004','연결구간 지연·반입 실패',55),'rapid':('R005','OHT 가동률 급락·Queue 급증',70),'silent':('R006','적재 상태의 완료 공백',80)}

def fmt(v):
 return f'{v:.6f}'.rstrip('0').rstrip('.') if isinstance(v,(float,int)) else str(v)
def code(v):return '<code>'+E(str(v))+'</code>'
def pill(s,kind=''):return '<span class="pill '+kind+'">'+E(s)+'</span>'
def tbl(head,rows,cls=''):
 return '<div class="table-wrap"><table class="'+cls+'"><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr class="search-row">'+''.join('<td>'+str(v)+'</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def active(f,k):
 if k.startswith('sorter'):return C['sorter_parameters'][f+'.'+k]['enabled']
 if k=='stb_cmd':return False
 if k in ['util_drop','qjump','zero']:return True
 if k.startswith('piofreq_'):return C['parameters'].get(f+'.pio_'+k[8:],{}).get('enabled',False)
 return C['parameters'].get(f+'.'+k,{}).get('enabled',False)
def targets(f,k):
 if k.startswith('sorter'):return ['일반 Sorter 별도 점수']
 if k in ['util_drop','qjump']:return ['R005']
 if k in ['q','growth']:return ['R002','R004']+(['R006'] if f=='M16HUB' else ['R003'])
 if k in ['time','sla']:return ['R001','R002','R004']+([] if f=='M16HUB' else ['R003'])
 if k=='loss':return ['R003']
 if k=='deficit':return ['R002','R003']
 if k in ['loaded','zero']:return ['R006','R002 확인']
 if k=='stb_cmd':return ['설명용']
 return ['R004']
def form(k):
 if k=='q':return '현재 미완료 JOB 수. HUB는 FOUP의 현재 위치가 HUB 내부인 JOB 수.'
 if k=='growth':return 'max(0, (Q(t)−Q(t−10)) / max(Q(t−10),20))'
 if k=='time' or k.startswith('cnvtime_'):return '0을 제외한 양수 완료시간의 최근 3분 중앙값 · 유효값 2개 이상'
 if k=='sla':return '4분 초과율의 최근 3분 중앙값 · 유효값 2개 이상'
 if k=='util_drop':return 'max(0, 직전 5분 가동률 중앙값−현재 가동률) · 현재값 제외'
 if k=='qjump':return 'max(0, 현재 Queue / 직전 5분 Queue 중앙값−1) · 현재값 제외'
 if k=='loss':return 'max(0, 1−최근10분 완료 / 기준 완료). 기준= t−39~t−10 값의 중앙값, 유효20개 이상'
 if k=='deficit':return 'max(0, (최근10분 생성−최근10분 완료) / 최근10분 생성)'
 if k=='loaded':return 'HUB 전체 적재 OHT 수 / HUB 운용 OHT 수'
 if k=='zero':return '최근 3분 중 완료시간=0인 분 수 · 3분 모두 유효해야 함'
 if k=='stb_cmd':return 'STB로 FOUP을 운반 중인 CMD 수 · 직접 가점 없음'
 if k.startswith('piofreq_'):return '최근 5분 중 PIO가 1건 이상 발생한 분 수 · 5분 모두 유효'
 if k.startswith('pio_'):return '1분 집계 DEPOSITED PIO의 최근 5분 합 · 5분 모두 유효'
 if k.startswith('sorter'):return '최근 5분 중앙값 · 유효값 3개 이상'
 if k.startswith('alt_'):return 'ALTERNATED 상태로 대기 중인 JOB 수 · 전체 JOB의 부분집합'
 return '원천 현재값 사용 · 방향/경로별 물량'
def threshold(f,k):
 if k=='stb_cmd':return '배점 없음'
 if k=='util_drop':return '동시 조건: 8%p 이상 하락 · 강도 상한 20%p'
 if k=='qjump':return '동시 조건: 5% 이상 증가 · 강도 상한 15%'
 if k=='zero':return '3분 중 2분 이상 0'
 if k.startswith('piofreq_'):return '5분 중 2분 이상 발생'
 p=C['sorter_parameters'].get(f+'.'+k) if k.startswith('sorter') else C['parameters'].get(f+'.'+k)
 if not p or not p['enabled']:return '비활성 · 임계값 미적용'
 lo,hi=p['low'],p['high'];s='L='+fmt(lo)+' / H='+fmt(hi)
 if k in ['growth','loss','deficit','loaded']:s+=' (비율 '+fmt(lo*100)+'% / '+fmt(hi*100)+'%)'
 return s

def rulecards(f):
 hub=f=='M16HUB';specs={k.split('.',1)[1]:v for k,v in C['features'].items() if k.startswith(f+'.')};cards=[]
 items=[('delay','반송을 끝내는 데 평소보다 오래 걸리는가?','최근3분의 완료 반송시간과4분 초과율을 확인합니다. 각 지표가 FAB별 기준을 얼마나 넘었는지 계산합니다.','둘 중 더 강한 지연 신호를 사용합니다. 두 값을 더하지 않습니다. 완료가 없는 분은 별도 해석이 필요합니다.','지연 강도가0.6이면45×0.6=27점입니다.','45 × D','D=max(S(완료시간3분 중앙값),S(4분 초과율3분 중앙값)). 비활성 지표 제외.'),
 ('backlog','끝내지 못한 반송이 쌓이고 있는가?','현재 미완료 JOB 수와10분 전 대비 증가율을 확인합니다. 다른 FAB에서는 생성 대비 완료 부족도 같이 봅니다.','미완료 물량의 수준과 증가를 결합합니다. 물량이 많다는 사실만으로 전체 정지를 뜻하지 않습니다.','최종 대기 강도가0.5이면40×0.5=20점입니다.','40 × B','B=max(0.65Q+0.35G,min(G,max(F,D))).')]
 if f=='M16A':items[1]=('backlog',items[1][1],items[1][2],'M16A Queue는2F·3F·6F 전체입니다. 반송 지연 또는 Queue 증가와 완료 부족이 함께 있는지를 확인해 가점을 조절합니다.',items[1][4],'40 × B × (0.25+0.75max(D,G×F))',items[1][6]+' 넓은 MCS 집계 범위에 대한 추가 확인 계수 적용.')
 if hub:items[1]=('backlog','HUB에 잠시 둔 물량이 해소되지 않는가?','HUB 내부 JOB와 예약 포함 저장률을 확인합니다. 저장률은5% 이상이5분 이상 이어질 때부터 저장대기 후보에 반영합니다.','정상적인 잠깐의 저장은 큰 위험으로 보지 않습니다. 지연·PIO·완료 공백이 함께 나타나면 가점을 높입니다. 내부JOB 대기와 저장대기를 중복 합산하지 않습니다.','저장 강도가1이어도 실제 반송 영향이 없으면 저장 기여10점, 영향 강도도1이면40점입니다.','40 × max(Bq×C, W×C)','Bq=max(0.65Q+0.35G,min(G,D)); C=0.25+0.75E; E=max(D,P,Z). W는 위 Storage 지속 강도.')
 if not hub:items.append(('completion','들어오는 반송을 처리하는 속도가 떨어졌는가?','최근10분 완료 JOB를 이전 처리 수준과 비교합니다. 동시에 Queue 증가·생성 대비 완료 부족·반송 지연 중 하나가 나타나는지 봅니다.','완료 감소만으로 가점하지 않습니다. 처리 감소 강도와 동반 문제 강도 중 작은 값으로 기여를 정합니다.','처리 감소 강도1, 동반 문제 강도0.5이면85×0.5=42.5점입니다.','85 × min(L,max(G,F,D))','이전 수준은 t−39~t−10의 최근10분 완료값 중앙값. 유효20개 이상. 10분값을 다시 합산하지 않음.'))
 items.append(('port','연결 장비에 FOUP을 내려놓지 못하는가?','방향별 AI Port의 DEPOSITED PIO를 최근5분 합계와 발생한 분 수로 확인합니다.','5분 중2분 이상 PIO가 발생하고 합계가 해당 경로 기준을 넘어야 기여가 생깁니다. 경로 대기·ALT·지연 등이 동반되면 더 크게 반영합니다.','Port 위험 강도0.6이면55×0.6=33점입니다.','55 × max(방향별 P)','P=S(PIO5분합)×(0.6+0.4max(S(경로물량),S(ALT),D,G)).'+(' M14A는 남·북 각각 min(S(CNV시간),S(CNV물량))도 MAX 후보.' if f=='M14A' else '')))
 if not hub:items.append(('rapid','OHT 가동률이 급락하면서 Queue가 갑자기 늘었는가?','현재를 제외한 직전5분 중앙값과 현재 OHT 가동률·Queue를 비교합니다.','가동률8%p 이상 하락과Queue5% 이상 증가가 동시에 있어야 합니다. 한 조건만 만족하면0점입니다.','두 조건을 막 충족하면40점, 두 변화가 더 심해질수록 최대70점입니다.','40 + 30 × min(u,q)','u=clip((가동률 하락폭−8)/12,0,1); q=clip((Queue 증가율−0.05)/0.10,0,1). 조건 미충족은0점.'))
 if hub:items.append(('silent','FOUP을 싣고 있는데 완료가 끊겼는가?','최근3분 중 완료시간이0인 분이2분 이상인지 확인합니다. 내부 JOB/Queue 증가와 적재OHT 비율도 같이 봅니다.','완료시간0만으로 장애로 보지 않습니다. 대기·적재 상태가 동반되는 정도에 따라 기여합니다. 진행 중 CMD 경과시간을 직접 측정한 값은 아닙니다.','대기·적재 동반 강도가0.5이면80×0.5=40점입니다.','80 × min(max(Q,G),S(적재OHT/운용OHT))','최근3분 중 완료시간0이2분 이상일 때만 적용. 실제 시간0 장애 사례의 독립 검증 미완료.'))
 for k,question,observe,condition,example,formula,detail in items:
  rid,name,cap=RULES[k]
  cols=[]
  for fk,v in specs.items():
   if active(f,fk) and any(t.startswith(rid) for t in targets(f,fk)):cols.extend(v['raw_columns'])
  if hub and k=='backlog':
   cols += ['M16HUB.STRATE.ALL.FABSTORAGERATIO']
   for fk,v in specs.items():
    if active(f,fk) and (fk in ['time','sla','loaded','zero'] or fk.startswith(('pio_','piofreq_','route_','alt_'))):cols.extend(v['raw_columns'])
  cols=list(dict.fromkeys(cols))
  cards.append('<article class="rule-card search-row" id="'+f+'-'+rid+'"><div class="rule-head">'+pill(rid)+'<strong>'+E(name)+'</strong><span>최대 '+str(cap)+'점</span></div><h4 class="question">'+E(question)+'</h4><dl><dt>무엇을 보나</dt><dd>'+E(observe)+'</dd><dt>언제 점수가 오르나</dt><dd>'+E(condition)+'</dd><dt>배점 예시</dt><dd>'+E(example)+'</dd></dl><details><summary>사용 원본 지표 '+str(len(cols))+'개 보기</summary>'+''.join('<div>'+code(col)+'</div>' for col in cols)+'</details><details><summary>정확한 계산식 보기</summary><div class="formula">'+E(formula)+'</div><p>'+E(detail)+'</p></details></article>')
 return '<div class="rules">'+''.join(cards)+'</div>'

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6fa;color:#1e304a;font:15px/1.65 "Malgun Gothic","Apple SD Gothic Neo",sans-serif}header{background:#102c50;color:white;padding:38px max(24px,calc((100vw - 1320px)/2)) 32px}.eyebrow{font-size:12px;letter-spacing:1.8px;color:#9fc4ed}h1{font-size:32px;margin:7px 0 9px;letter-spacing:-1px}h2{font-size:24px;letter-spacing:-.5px;margin:0 0 14px}h3{font-size:18px;margin:30px 0 10px}h4{margin:0 0 8px}p{margin:7px 0 14px}.meta{color:#c9daee;font-size:13px}nav{position:sticky;top:0;background:#fff;z-index:5;box-shadow:0 2px 12px #16335914;border-bottom:1px solid #dce3ed}.navinner{max-width:1368px;margin:auto;padding:12px 24px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}button{font:inherit;border:1px solid #cbd8e7;background:white;padding:8px 15px;border-radius:7px;color:#183c67;cursor:pointer}button.active{background:#1957a0;border-color:#1957a0;color:white}button:hover{border-color:#1957a0}input[type=search]{flex:1;min-width:240px;font:inherit;padding:9px 12px;border:1px solid #cbd8e7;border-radius:7px}main{max-width:1368px;margin:auto;padding:24px}.intro,.panel,.common{background:white;border:1px solid #dee6ef;border-radius:12px;padding:28px;margin-bottom:24px}.chips{display:flex;gap:7px;flex-wrap:wrap}.pill{display:inline-block;background:#eaf1fa;color:#20518a;border-radius:4px;padding:2px 7px;font-size:12px;white-space:nowrap}.muted{background:#f0f1f4;color:#586577}.good{background:#e5f5f0;color:#18614e}.warn{background:#fff3df;color:#855014}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.flow>div{background:#f1f6fc;border-top:3px solid #3a78bd;padding:15px}.flow small{display:block;color:#5f7795;margin-top:6px}.flow b{display:block;margin-top:2px}.flow .n{font-size:12px;color:#447ab2}.scope{font-size:17px;color:#426489}.notice{border-left:4px solid #4785c8;background:#edf5ff;padding:13px 17px;margin:16px 0}.notice.amber{border-color:#c88e31;background:#fff7e8}.table-wrap{overflow-x:auto;margin:14px 0 24px}table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}th{background:#eaf0f7;text-align:left;padding:11px 12px;font-size:12px;vertical-align:top}td{padding:12px;vertical-align:top;border-bottom:1px solid #e5ebf2;overflow-wrap:anywhere}tr:nth-child(even){background:#fafcfe}code{font:12px/1.6 Consolas,monospace;overflow-wrap:anywhere;word-break:break-word;color:#245d87}td small{display:block;color:#667990;margin-top:5px}a{color:#165ba5;text-decoration:none}a:hover{text-decoration:underline}.raw th:nth-child(1){width:39%}.raw th:nth-child(2){width:18%}.raw th:nth-child(3){width:28%}.raw th:nth-child(4){width:15%}.derived th:nth-child(1){width:20%}.derived th:nth-child(2){width:25%}.derived th:nth-child(3){width:23%}.derived th:nth-child(4){width:22%}.derived th:nth-child(5){width:10%}.rules{display:grid;grid-template-columns:1fr 1fr;gap:14px}.rule-card{border:1px solid #d8e3ef;border-radius:8px;padding:19px}.rule-head{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.rule-head span:last-child{margin-left:auto;font-size:13px;color:#58738e}.question{margin-top:17px;font-size:17px;color:#153f70}.rule-card dl{margin:0}.rule-card dt{font-size:12px;font-weight:bold;color:#426b97;margin-top:12px}.rule-card dd{margin:4px 0 0;font-size:14px}.rule-card details{margin:12px 0 0;padding:10px;font-size:12px}.rule-card p{font-size:13px;color:#486079;margin-bottom:0}.formula{padding:12px 14px;background:#f3f6fb;margin:13px 0;font:14px/1.7 Consolas,"Malgun Gothic",monospace;overflow-wrap:anywhere}details{margin:20px 0;border:1px solid #dde5ef;border-radius:8px;padding:15px}summary{cursor:pointer;font-weight:bold}.small{font-size:13px;color:#61738b}.sectionlinks{display:flex;gap:20px;flex-wrap:wrap;font-size:13px;margin:15px 0}.legend{display:flex;gap:15px;flex-wrap:wrap}.hidden,[hidden]{display:none!important}.scorebands{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:16px 0}.scorebands div{padding:12px;border-radius:7px;background:#eaf1f9}.scorebands div:nth-child(2){background:#fff6d9}.scorebands div:nth-child(3){background:#ffeacb}.scorebands div:nth-child(4){background:#ffe0df}.calc{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}.fields{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fields label{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13px}.fields input{width:88px;padding:8px;border:1px solid #cbd8e7;border-radius:5px;font:inherit}.result{background:#edf4fc;padding:20px;border-radius:8px}.result strong{font-size:38px;color:#1557a0}.result p{font-size:13px}.footer{font-size:12px;color:#637892;margin:20px 0 35px}.count{font-size:12px;color:#657f99;margin-left:5px}.tabular{font-variant-numeric:tabular-nums}.nohits{padding:15px;color:#825825}body.printall .panel{display:block!important}@media(max-width:850px){header{padding:25px 18px}h1{font-size:26px}main{padding:14px}.intro,.panel,.common{padding:18px}.rules,.calc{grid-template-columns:1fr}.flow{grid-template-columns:1fr 1fr}.navinner{padding:10px 14px}table{min-width:700px}}@media print{nav,.calc,.sectionlinks,.no-print{display:none!important}body{background:white;font-size:11px}header{background:white;color:#17375c;padding:10px 0}.meta,.eyebrow{color:#426489}main{padding:0;max-width:none}.intro,.panel,.common{border:0;padding:12px 0}.panel{display:block!important;break-before:page}table{font-size:10px;min-width:0}td,th{padding:7px}.rule-card{break-inside:avoid}.flow{break-inside:avoid}.search-row{display:revert!important}details>*{display:block}a{color:inherit}}'''
parts=['<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FAB별 지표와 스코어링 룰 · v1.2</title><style>'+CSS+'</style></head><body>',f'<header><div class="eyebrow">AMHS · RULE GUIDE</div><h1>FAB별 지표와 스코어링 룰</h1><p>원천 지표에서 최종 위험 점수까지, 실제 v1.2 설정으로 확인합니다.</p><div class="meta">룰 v1.2 · 설명자료 2026-09-28 · 설정 ID {C["config_id"]} · 8/11–9/11 설계기간 기준</div></header>', '<nav><div class="navinner">'+''.join('<button class="fabbtn" data-fab="'+f+'">'+('HUBROOM' if f=='M16HUB' else f)+'</button>' for f in FABS)+'<button class="fabbtn" data-fab="all">전체 FAB</button><input id="search" type="search" aria-label="지표명 또는 룰 검색" placeholder="지표명·파생명·룰 검색"><button id="print">전체 인쇄</button></div></nav><main>', '<section class="intro"><h2>읽는 순서</h2><div class="flow"><div><span class="n">01 · INPUT</span><b>원천 지표</b><small>원본 컬럼명과 집계 범위 확인</small></div><div><span class="n">02 · FEATURE</span><b>파생 지표</b><small>시간창·증가율·실제 L/H 임계값</small></div><div><span class="n">03 · RULE</span><b>룰별 기여</b><small>동반 조건과 룰별 최대 배점</small></div><div><span class="n">04 · SCORE</span><b>최종 점수</b><small>상위 기여 합성·추세·회복 확인</small></div></div><div class="legend">'+pill('원천. 입력값')+pill('파생. 계산값')+pill('룰. 기여값')+pill('점수. 합성 결과')+'</div><p class="small">원본 CSV 컬럼은 변경하지 않습니다. 표시명에 붙인 접두어는 역할을 구분하기 위한 것입니다. PIO 원본 컬럼은 예외적으로 화살표·밑줄 표기를 그대로 사용합니다.</p><div class="notice">FAB 반송 위험과 일반 Sorter 대기 점수는 별도입니다. CU Sorter는 미평가이며 일반 Sorter와 MAX로 결합하지 않습니다. 100점은 산식의 상한이며, 전체 FAB 마비 확정 또는 장애확률 100%를 뜻하지 않습니다.</div><p class="small">자료는 실제 코드·고정 설정에서 추출했습니다. 일반 Sorter만 산정하도록 v1.2로 개정했습니다. FAB 반송 위험 산식은 v1.1을 유지합니다. 9/12–15 원천 독립 평가는 아직 미완료입니다.</p></section>']
audit={}
for f in FABS:
 specs={k.split('.',1)[1]:v for k,v in C['features'].items() if k.startswith(f+'.')};rawmap={}
 for k,v in specs.items():
  for col in v['raw_columns']:rawmap.setdefault(col,[]).append(k)
 if f=='M16HUB':
  for col in ['M16HUB.STRATE.ALL.FABSTORAGERATIO','M16HUB.STRATE.STB.3F_STORAGE_UTIL','M16HUB.STRATE.STK.STORAGERATIO']:rawmap.setdefault(col,[])
 activecols=[r for r,ks in rawmap.items() if any(active(f,k) for k in ks) or r=='M16HUB.STRATE.ALL.FABSTORAGERATIO']
 audit[f]={'active_raw_columns':activecols,'features':specs}
 parts += [f'<section class="panel" data-panel="{f}" id="{f}"><h2>{f if f!="M16HUB" else "M16HUB · HUBROOM"}</h2><p class="scope">{E(SCOPE[f])}</p><div class="notice">{E(NOTES[f])}</div><div class="chips">'+pill('사용 원천 '+str(len(activecols))+'개 · Sorter 포함','good')+pill('파생 '+str(len(specs))+'개'+(' + Storage 분기' if f=='M16HUB' else ''))+'</div><div class="sectionlinks">'+''.join(f'<a href="#{f}-{anchor}">{name}</a>' for anchor,name in [('raw','① 원천 지표'),('features','② 파생·임계값'),('rules','③ 룰별 기여'),('output','④ 출력·최종 합성')])+'</div>',f'<h3 id="{f}-raw">① 사용하는 원천 지표</h3>']
 rr=[]
 for col,ks in rawmap.items():
  act=[k for k in ks if active(f,k)];typ='배점 사용' if act else '배점 비활성';note='';label=' / '.join(dict.fromkeys(specs[k]['display'].split('.',2)[-1] for k in ks))
  if act and all(k.startswith('sorter') for k in act):typ='Sorter 전용'
  if not act and any(k.startswith('sorter') for k in ks):typ='CU 미평가';note='CU Sorter는 별개의 장비. 이번 버전은 일반 Sorter만 평가하므로 CU는 미평가(정상0점 아님).'
  if ks==['sla'] and not act:note='현재 고정 설정 enabled=false. 지표가 존재해도 배점하지 않음.'
  if col=='M16HUB.STRATE.ALL.FABSTORAGERATIO':typ='배점 사용';label='예약 포함 HUBROOM 저장률';note='높을수록 저장 부담 증가. Reserved 카운트 포함.'
  if col=='M16HUB.STRATE.STB.3F_STORAGE_UTIL':typ='참고용';label='HUB STB 빈 공간 비율';note='높을수록 여유. 100−이 값으로 예약 포함 저장률을 만들지 않음.'
  if col=='M16HUB.STRATE.STK.STORAGERATIO':typ='제외';label='HUB STK 비율';note='HUBROOM에 STK가 없음.'
  if 'stb_cmd' in ks:typ='참고용';note='운반 중인 적재 OHT 수. 저장된 FOUP 수 아님. MAXCAPA 외 사유 포함.'
  if col.endswith(('CURRENTQCREATED','CURRENTQCOMPLETED')):note='최근10분 MCS JOB 건수. CMD/FABJOB 건수가 아니며 다시10분 합산하지 않음.'
  if 'CURRENT_M16A_3F_JOB_2' in col:note='FOUP 현재 위치가 HUBROOM 내부인 JOB 수.'
  if col=='M16A.QUE.ALL.CURRENTQCNT':note='M16A MCS 전체: 2F·3F·6F 포함. 6F 전용 아님.'
  if 'PIOERROR' in col:note='출발 영역의 AI 내려놓기 실패(DEPOSITED), 1분 집계. 이웃 FAB에 자동 전파하지 않음.'
  links=' '.join('<a href="#'+f+'-feature-'+k+'">'+E(k)+'</a>' for k in ks) or ('<a href="#M16HUB-storage">Storage 분기</a>' if typ=='배점 사용' else '—')
  rr.append([code(col)+'<small>'+E(label)+'</small>',pill(typ,'good' if typ in ['배점 사용','Sorter 전용'] else 'muted'),E(note) if note else E('완료시간은 종료된 CMD만 반영. 완료 없는 분의0을 지연 개선으로 단정하지 않음.' if 'TIME' in col else '방향·범위를 유지하여 파생 계산에 사용.'),links])
 parts.append(tbl(['원본 컬럼명 / 의미','사용 구분','집계·해석 주의','연결 파생ID'],rr,'raw'))
 # Other available raw columns: distinguish score-active from merely held data.
 others=[]
 for row in D:
  col=row['원본CSV컬럼']
  if col.startswith(prefix[f]+'.') and col not in rawmap:
   status=row['상태'];status='직접 사용 안 함 · '+status if '제외' not in status else status
   others.append([code(col),E(status)])
 parts.append('<details><summary>그 밖의 보유 지표 · 참고/미채택/제외 <span class="count">'+str(len(others))+'개</span></summary><p class="small">현재 점수에 직접 투입하지 않는 항목입니다. MAXCAPA 변경 등은 운영 맥락이며 변경 자체로 가점하지 않습니다. WT·PKT, 6ABL60 계열의 잘못된2F 지표, 위치를 알 수 없는 HTSTOP/CONGESTED/ABNORMAL 등은 제외 원칙을 유지합니다.</p>'+tbl(['원본 컬럼명','현재 상태'],others)+'</details>')
 parts.append(f'<h3 id="{f}-features">② 파생 지표와 실제 임계값</h3><p>일반 심각도 <b>S(x)=clip((x−L)/(H−L),0,1)</b>. L 이하는0, H 이상은1입니다. L/H는 원천값이 아니라 아래 파생값에 적용합니다.</p><p class="small">증가율·감소율은 코드상0~1 비율입니다. 0.15는15%입니다. 가동률 하락폭은%p입니다. 시간은 원천 시간단위를 유지합니다. L/H만으로 알람이 발생하는 것은 아니며 룰의 동반 조건을 거칩니다.</p>')
 fr=[]
 for k,v in specs.items():
  act=active(f,k);status='사용' if act else ('참고' if k=='stb_cmd' else '미평가' if k=='sorter_cu' else '비활성')
  title='<div id="'+f+'-feature-'+k+'">'+E(v['display'].split('.',2)[-1])+'</div>'+code(f+'.'+k)+' '+pill(status,'good' if act else 'muted')
  fr.append([title, '<br>'.join(code(col) for col in v['raw_columns']), E(form(k)),E(threshold(f,k)),E(' · '.join(targets(f,k))) if act else '직접 가점 없음'])
 parts.append(tbl(['파생 표시명 / ID','사용한 원본 지표명','계산 방식','실제 적용 임계값','연결 룰'],fr,'derived'))
 if f=='M16HUB':
  parts.append('<h3 id="M16HUB-storage">HUB 전용 · 예약 포함 저장대기</h3><p>다른 FAB의 상시 높은 Storage 점유에는 적용하지 않는 HUB 전용 후보 기준입니다.</p>'+tbl(['파생 단계','정확한 조건','사용 원본 지표 / 의미'],[
 ['입력 U',code('M16HUB.STRATE.ALL.FABSTORAGERATIO'),'Reserved 포함 저장률 · 유효 범위0~100%'],
 ['수준 R','U3=최근3분 중앙값(3개 모두 유효). R=clip((U3−5)/15,0,1)',code('M16HUB.STRATE.ALL.FABSTORAGERATIO')+'<small>5%에서0,20%에서1</small>'],
 ['지속 n','원천 U≥5%가 연속된 분 수. 5% 미만/결측이면 끊음',code('M16HUB.STRATE.ALL.FABSTORAGERATIO')+'<small>개별 FOUP 체류시간 아님</small>'],
 ['지속계수 T','n&lt;5이면0, n≥5이면min(n/10,1)',code('M16HUB.STRATE.ALL.FABSTORAGERATIO')+'<small>5분에0.5,10분부터1</small>'],
 ['해소 확인','U(t)−U(t−5)≤−2%p이면 W=0, 그 외 W=R×T',code('M16HUB.STRATE.ALL.FABSTORAGERATIO')+'<small>최근5분간2%p 이상 감소 시 저장 후보 가점 중단</small>'],
 ['반송 영향 확인','E=max(D,P,Z), C=0.25+0.75E','D·P·Z의 사용 원천은 위 파생표와 아래 R001/R004/R006 입력 목록에 전부 표시. 해당 룰 강도를 재사용하며 원천 추가 없음.'],
 ['대기 룰 결합','40×max(Bq×C,W×C)',code('M16HUB.QUE.ALL.CURRENT_M16A_3F_JOB_2')+'<br>'+code('M16HUB.STRATE.ALL.FABSTORAGERATIO')+'<small>D/P/Z 확인계수 적용. 두 후보 MAX; CMD 가점 없음.</small>']
 ])+'<div class="notice amber">5%/20%, 5분/10분, 해소2%p는 동작 원리를 반영한 후보값입니다. 실제 장애 정답으로 최적화한 값은 아닙니다. 저장률이 결측이면 저장 기여를 제외하고 품질 표시를 남깁니다.</div>')
 parts.append(f'<h3 id="{f}-rules">③ 룰별 기여</h3><p class="small">아래 Q·G·D·F·L·P·Z는 원천 개수가 아닌0~1 심각도입니다. 각 룰의 최대 배점을 모두 더해 최종점수를 만들지 않습니다.</p>'+rulecards(f))
 if f!='M16HUB':parts.append('<article class="rule-card"><div class="rule-head">'+pill('S001')+'<strong>일반 Sorter 대기 · 별도 점수</strong><span>0~100점</span></div><p>일반 Sorter의 대기가 해당 FAB 일반 Sorter 기준보다 얼마나 높은지 평가합니다. 다른 장비보다 큰지를 비교하지 않습니다.</p><p>사용 원본: '+code(prefix[f]+'.SORTER.ABN.SORTERWAITCOUNTOVER')+'</p><div class="formula">100 × clip((최근5분 중앙값−L)/(H−L),0,1)</div><p>일반 Sorter의 대기량만 그 장비의 기준으로 평가합니다. CU Sorter와 비교하거나 합치지 않습니다. CU Sorter는 미평가입니다. FAB 반송 점수에 합산하지 않습니다. Sorter 작업이 실제 반송 지연·PIO 등을 유발한 경우에는 해당 관측값이 기존 반송 룰에 반영됩니다.</p></article>')
 parts.append(f'<h3 id="{f}-output">④ 출력과 최종 합성</h3><p><b>점수.FAB반송위험</b>은 아래 공통 합성 절차를 거친0~100점입니다. <b>설명.주요위험</b>은 가장 큰 룰 기여 또는 회복 확인 상태를 표시합니다.</p>')
 if f=='M16HUB':parts.append('<p class="small">추가 출력: 예약 포함 저장률, 빈 공간 비율, STB행 CMD, 저장률3분 중앙값, 기준이상 연속분수,5분변화,Storage 상태,품질.HUB 저장률 유효,내부JOB·저장대기 후보별 기여. 두 후보 기여는 최종에 따로 더하지 않습니다.</p>')
 core=['현재 Queue','현재1분 완료시간']+(['최근10분 생성','최근10분 완료'] if f!='M16HUB' else ['전체 적재OHT 수','운용OHT 수'])
 parts.append('<p class="small">필수 현재 입력: '+E(' · '.join(core))+' 및10분 전 Queue. 없으면 판단불가로 내보냅니다. 선택 입력 결측은 해당 기여를 제외하되 관측품질로 구분합니다. 매 행에 룰버전1.1과 설정ID를 기록합니다.</p></section>')
parts.append('''<section class="common" id="common"><h2>공통 · 최종 점수 산정</h2><div class="scorebands"><div><b>0 ≤ 점수 &lt; 20</b><br>낮음</div><div><b>20 ≤ 점수 &lt; 40</b><br>주의</div><div><b>40 ≤ 점수 &lt; 70</b><br>경고</div><div><b>70 ≤ 점수 ≤ 100</b><br>위험</div></div><ol><li><b>상위 기여 합성:</b> 룰 기여를 큰 순서로 r1,r2,r3라 하면 기본점수=min(100,r1+0.30r2+0.15r3).</li><li><b>추세 보정:</b> 15점 이상 기여 룰이2개 이상일 때 min(10,0.25×max(기본점수(t)−기본점수(t−5)−15,0)). 그 외0. 최종점수를 다시 입력으로 넣지 않습니다.</li><li><b>현재 합성값:</b> min(100,기본점수+추세보정).</li><li><b>일시 변동 완화:</b> 현재 포함 최근3분 합성값의 중앙값(유효2개 이상). R003≥70 또는 R005≥40일 때는 현재 합성값으로 즉시 상승 가능.</li><li><b>회복 확인:</b> 최종점수는 직전 최종점수보다 분당 최대5점 하락. 필수입력 결측이면 판단불가로 처리하고 하락 상태 초기화. 출력은 소수점1자리.</li></ol><div class="notice">평소 높은 저장 점유율인 M14A/B·M16A/B에는 HUB의 빈 공간 원칙과5%/20% 기준을 적용하지 않습니다. MAXCAPA의 감소만으로 장애를 확정하거나 인접 FAB 점수를 자동으로 올리지 않습니다.</div><h3>기여값 합성 계산 예시</h3><p class="small">아래는 원천→파생 계산이 끝난 <b>룰별 기여값</b>을 직접 넣는 예시입니다. 3분 중앙값과 하락 완화 전의 현재 합성값을 보여주며 운영 점수 계산기를 대체하지 않습니다.</p><div class="calc"><div class="fields">''')
for k in ['delay','backlog','completion','port','rapid','silent']:
 rid,name,cap=RULES[k];val=85 if k=='completion' else 30.94 if k=='backlog' else 0
 parts.append(f'<label>{E(name)}<input class="contribution" id="calc-{k}" type="number" min="0" max="{cap}" step="0.01" value="{val}" aria-label="{E(name)} 기여값"></label>')
parts.append('''<label>5분 전 기본점수<input id="previousBase" type="number" min="0" max="100" step="0.01" value="10" aria-label="5분 전 기본점수"></label></div><div class="result"><div>현재 합성값 · 필터 적용 전</div><strong id="calc-result"></strong><p id="calc-explain"></p><p>초기값은8/26 M16A10:08의 기여값을 반올림해 넣은 예시입니다. 기본94.28점에 추세10점이 더해져100점 상한에 도달했습니다. OHT STOP이라는 작업명으로 가점한 것이 아닙니다.</p></div></div><h3>도메인과 판단의 경계</h3><ul><li>JOB은 MCS 단위 반송, CMD는 개별 장비 반송, FABJOB은 FAB 간 반송입니다. 최근10분 생성·완료는 MCS JOB입니다.</li><li>완료시간 평균은 미완료 CMD의 경과시간을 직접 보여주지 않습니다. 완료0과 결측은 서로 다릅니다.</li><li>MAXCAPA는 입구 물량 제어 설정입니다. 6ABL 3F AI는 별도 TOTALMAXCAPA/ALTMAXCAPA(현재280) 예외가 있어 수집한 MAXCAPA 합을 넘는 반송도 가능합니다.</li><li>MLUD의 MO 수동 출고 지연은 AI 점유·PIO·HUB 정체로 이어질 수 있으나 PIO만으로 데드락을 확정하지 않습니다. MMDM 수동 분기와6ACNVB01 수동 출고 경로는 운영 맥락입니다.</li><li>이 자료의 배점·임계값은 v1.2 구현을 설명합니다. 독립 평가 미완료 상태이며 자동 장비 제어는 하지 않습니다.</li></ul><details><summary>버전·근거 및 변경 이력</summary><p>룰 버전1.1, 개정일2026-09-28, 설정ID7e257816335e0778. 부모 설정ID7c6396b695153b20. 설명자료는 실행패키지의 fab_risk_rules.py, rule_config.json, source_dictionary.csv, RULES.md, HUBROOM_domain.md를 기준으로 작성했습니다.</p><p>v1.1: HUB 예약 포함 저장률·지속 대기·반송영향 결합. v1.2: 일반/CU Sorter를 별개 장비로 정정하고 일반 Sorter만 평가. 모든 FAB 반송 위험 점수는 v1.1과 같습니다.</p><p>파생표에 사용한 원본 지표명을 추가하고, 룰 설명을 판단 조건 중심으로 개편했습니다. 이전 실행패키지는 새 패키지 history에 보존했습니다. 결과 컬럼은 점수.일반Sorter대기와 등급.일반Sorter대기로 변경됩니다.</p></details></section><div class="footer">FAB 위험 룰 설명자료 · v1.2 · 외부 라이브러리나 인터넷 연결 없이 사용 가능 · 전체 인쇄 시5개 FAB가 모두 포함됩니다.</div></main>''')
parts.append('<script id="rule-metadata" type="application/json">'+json.dumps({'config_id':C['config_id'],'version':C['version'],'parameters':C['parameters'],'sorter_parameters':C['sorter_parameters'],'fab_mapping':audit},ensure_ascii=False).replace('<','\\u003c')+'</script>')
parts.append('''<script>
(()=>{let selected='M14A';const buttons=[...document.querySelectorAll('.fabbtn')],panels=[...document.querySelectorAll('.panel')],search=document.getElementById('search');function apply(){const term=search.value.trim().toLowerCase();buttons.forEach(b=>{b.classList.toggle('active',b.dataset.fab===selected);b.setAttribute('aria-pressed',String(b.dataset.fab===selected))});panels.forEach(p=>{p.hidden=selected!=='all'&&p.dataset.panel!==selected;p.querySelectorAll('.search-row').forEach(r=>r.hidden=!!term&&!r.textContent.toLowerCase().includes(term));p.querySelectorAll('details').forEach(d=>{if(term)d.open=!![...d.querySelectorAll('.search-row')].some(r=>!r.hidden)})})}buttons.forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.fab;apply()}));search.addEventListener('input',apply);document.getElementById('print').addEventListener('click',()=>{search.value='';selected='all';apply();document.querySelectorAll('details').forEach(d=>d.open=true);window.print()});function calc(){const vals=[...document.querySelectorAll('.contribution')].map(i=>Math.min(+i.max,Math.max(0,+i.value||0))).sort((a,b)=>b-a),base=Math.min(100,vals[0]+.30*vals[1]+.15*vals[2]),old=Math.min(100,Math.max(0,+document.getElementById('previousBase').value||0)),trend=vals.filter(x=>x>=15).length>=2?Math.min(10,.25*Math.max(0,base-old-15)):0;document.getElementById('calc-result').textContent=Math.min(100,base+trend).toFixed(2);document.getElementById('calc-explain').textContent=`상위 기여 ${vals[0].toFixed(2)} + 0.30 × ${vals[1].toFixed(2)} + 0.15 × ${vals[2].toFixed(2)} → 기본 ${base.toFixed(2)}점 + 추세 ${trend.toFixed(2)}점`;}document.querySelectorAll('.calc input').forEach(i=>i.addEventListener('input',calc));apply();calc();})();
</script></body></html>''')
out=(P/'FAB별_지표와_스코어링룰_v1_2_설명.html');out.write_text(''.join(parts),encoding='utf-8')
print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'active_raw_counts':{f:len(audit[f]['active_raw_columns']) for f in FABS}},ensure_ascii=False))
