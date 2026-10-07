"""FAB transport risk v1.2. Frozen calibration; causal features only.
Python 3.10+, numpy, pandas. Scores are severity indices, not probabilities.
"""
from pathlib import Path
import argparse,json,zipfile,hashlib
import numpy as np
import pandas as pd
FABS=['M14A','M14B','M16A','M16B','M16HUB']
PREFIX={'M14A':'M14','M14B':'M14B','M16A':'M16A','M16B':'M16B','M16HUB':'M16HUB'}
TIME_COLUMNS={f:PREFIX[f]+('.QUE.TIME.AVGTOTALTIME1MIN' if f in ['M14B','M16HUB'] else '.QUE.LOAD.AVGLOADTIME1MIN') for f in FABS}
ROUTES={
 'M14A': [('HUB','M14.QUE.ALL.3F_TO_HUB_JOB','M14.QUE.ALL.3F_TO_HUB_JOB_ALT','M16HUB<-M14A_PIOERROR_DEPOSITED'),('M14B',None,None,'M14A->M14B_PIOERROR_DEPOSITED')],
 'M14B': [('HUB','M14B.QUE.ALL.7F_TO_HUB_JOB','M14B.QUE.ALL.7F_TO_HUB_JOB_ALT','M16HUB<-M14B_PIOERROR_DEPOSITED'),('M14A','M14B.LFT.SENDFAB.TO_M14A_CURRENTQCNT',None,'M14A<-M14B_PIOERROR_DEPOSITED')],
 'M16A': [('HUB','M16A.QUE.ALL.6F_TO_HUB_JOB','M16A.QUE.ALL.6F_TO_HUB_JOB_ALT','M16HUB<-M16A_PIOERROR_DEPOSITED'),('M16B','M16A.LFT.SENDFAB.TO_M16B_CURRENTQCNT',None,'M16A->M16B_PIOERROR_DEPOSITED')],
 'M16B': [('M16A','M16B.LFT.SENDFAB.TO_M16A_CURRENTQCNT',None,'M16B->M16A_PIOERROR_DEPOSITED')],
 'M16HUB': [('M14A','M16HUB.QUE.ALL.3F_TO_M14A_3F_JOB',None,'M16HUB->M14A_PIOERROR_DEPOSITED'),('M14B','M16HUB.QUE.ALL.3F_TO_M14B_7F_JOB',None,'M16HUB->M14B_PIOERROR_DEPOSITED'),('M16A','M16HUB.QUE.ALL.3F_TO_M16A_6F_JOB',None,'M16HUB->M16A_PIOERROR_DEPOSITED'),('MLUD','M16HUB.QUE.MLUD.3F_TO_M16A_MLUD_AI_CMD',None,'M16HUB->MLUD_PIOERROR_DEPOSITED')]
}
RULE_NAMES={'delay':'반송 지연 지속','backlog':'미완료 물량 누적','completion':'처리 감소와 대기 증가','port':'연결구간 지연·반입 실패','silent':'적재 상태의 완료 공백','rapid':'OHT 가동률 급락·Queue 급증','trend':'최근 5분 위험 급상승'}
STORAGE_USED='M16HUB.STRATE.ALL.FABSTORAGERATIO'
STORAGE_FREE='M16HUB.STRATE.STB.3F_STORAGE_UTIL'
STORAGE_CMD='M16HUB.QUE.STB.3F_TO_M16A_3F_STB_CMD'

def storage_context(d,cfg):
 """Aggregate level persistence, not individual FOUP dwell or timer executions."""
 p=cfg['hub_storage'];u=raw(d,STORAGE_USED);u=u.where(u.between(0,100))
 free=raw(d,STORAGE_FREE);free=free.where(free.between(0,100))
 med=u.rolling(3,min_periods=3).median().where(u.notna())
 on=u.ge(p['low_pct']);n=on.groupby((~on).cumsum()).cumsum().astype(float)
 strength=((med-p['low_pct'])/(p['high_pct']-p['low_pct'])).clip(0,1)
 duration=(n/p['full_persistence_minutes']).clip(0,1).where(n>=p['min_persistence_minutes'],0)
 delta=u-u.shift(p['release_window_minutes'])
 clearing=delta.le(-p['release_drop_pp'])
 severity=(strength*duration).where(~clearing,0).where(u.notna())
 state=pd.Series('낮은 대기',index=d.index)
 state=state.mask(on,'일시 대기').mask(on & (n>=p['min_persistence_minutes']),'예약 포함 저장률 지속')
 state=state.mask(clearing,'대기 해소 중').mask(u.isna(),'저장률 판단불가')
 return pd.DataFrame({'used':u,'free':free,'cmd':raw(d,STORAGE_CMD),'median':med,'minutes':n.where(u.notna()),'delta':delta,'severity':severity,'state':state,'valid':u.notna()},index=d.index)
def load_data(path):
 """Read original CSV/ZIP/directory; never execute content; max 200 files/512MB."""
 path=Path(path);frames=[];meta=[]
 if path.suffix.lower()=='.zip':
  with zipfile.ZipFile(path) as z:
   ns=[x for x in z.infolist() if x.filename.lower().endswith('.csv')]
   if len(ns)>200 or sum(x.file_size for x in ns)>512*1024**2:raise ValueError('Input limit exceeded')
   for n in sorted(ns,key=lambda x:x.filename):
    with z.open(n) as f: a=pd.read_csv(f,encoding='utf-8-sig')
    meta.append({'file':n.filename,'rows':len(a),'columns':len(a.columns)});frames.append(a)
 else:
  paths=[path] if path.is_file() else sorted(path.glob('*.csv'))+sorted(path.glob('*.CSV'))
  if len(paths)>200:raise ValueError('Input file limit exceeded')
  for n in paths:
   a=pd.read_csv(n,encoding='utf-8-sig');meta.append({'file':n.name,'rows':len(a),'columns':len(a.columns)});frames.append(a)
 if not frames:raise ValueError('No CSV found')
 a=pd.concat(frames,ignore_index=True)
 if 'CRT_TM' not in a:raise ValueError('Required time column CRT_TM is missing')
 t=pd.to_datetime(a.pop('CRT_TM'),errors='coerce')
 if t.isna().any():raise ValueError('Invalid timestamps; correct input before scoring')
 if t.duplicated().any():raise ValueError('Duplicate timestamps; resolve explicitly before scoring')
 if not t.eq(t.dt.floor('min')).all():raise ValueError('Timestamps must be minute aligned')
 a=a.apply(pd.to_numeric,errors='coerce');a.index=t;a=a.sort_index()
 if (a.index[-1]-a.index[0]).days>180:raise ValueError('Time range exceeds 180-day guard')
 a=a.reindex(pd.date_range(a.index.min(),a.index.max(),freq='min'));a.index.name='time'
 a=a.mask(a<0) # counts, minutes and percentages in this package must be nonnegative
 return a,meta

def raw(d,k):return d[k].astype(float) if k and k in d else pd.Series(np.nan,index=d.index)
def maximum(*xs):return pd.concat(xs,axis=1).max(axis=1,skipna=True)
def minimum(*xs):return pd.concat(xs,axis=1).min(axis=1,skipna=False)
def features(d):
 z={};spec={};cores={}
 def add(f,k,s,cols,label):
  key=f+'.'+k;z[key]=s;spec[key]={'display':'파생.'+f+'.'+label,'raw_columns':[x for x in cols if x], 'feature_id':key};return s
 for f in FABS:
  p=PREFIX[f];qk=p+'.QUE.ALL.CURRENTQCNT' if f!='M16HUB' else 'M16HUB.QUE.ALL.CURRENT_M16A_3F_JOB_2'
  q=raw(d,qk);add(f,'q',q,[qk],'현재 영역 물량')
  add(f,'growth',((q-q.shift(10))/q.shift(10).clip(lower=20)).clip(lower=0),[qk],'최근10분 물량 증가율')
  tk=TIME_COLUMNS[f];sk=p+'.QUE.ALL.TRANSPORT4MINOVERRATIO'
  tm=raw(d,tk);sla=raw(d,sk)
  add(f,'time',tm.where(tm>0).rolling(3,min_periods=2).median(),[tk],'완료반송시간 3분 중앙값')
  add(f,'sla',sla.rolling(3,min_periods=2).median(),[sk],'4분초과율 3분 중앙값')
  if f!='M16HUB':
   ck=p+'.QUE.ALL.CURRENTQCREATED';ek=p+'.QUE.ALL.CURRENTQCOMPLETED';c=raw(d,ck);e=raw(d,ek)
   ref=e.shift(10).rolling(30,min_periods=20).median()
   uk=p+'.QUE.OHT.OHTUTIL';u=raw(d,uk)
   add(f,'util_drop',(u.shift(1).rolling(5,min_periods=5).median()-u).clip(lower=0),[uk],'직전5분 대비 OHT가동률 하락폭')
   add(f,'qjump',(q/q.shift(1).rolling(5,min_periods=5).median().replace(0,np.nan)-1).clip(lower=0),[qk],'직전5분 대비 Queue 증가율')
   add(f,'loss',(1-e/ref.replace(0,np.nan)).clip(lower=0),[ek],'과거처리수준 대비 완료감소율')
   add(f,'deficit',((c-e)/c.replace(0,np.nan)).clip(lower=0),[ck,ek],'최근10분 생성대비 완료부족률')
   cores[f]=pd.concat([q,c,e,tm],axis=1).notna().all(axis=1)
  else:
   cmdk='M16HUB.QUE.ALL.3F_CMD';cntk='M16HUB.QUE.OHT.CURRENTOHTQCNT'
   add(f,'loaded',raw(d,cmdk)/raw(d,cntk).replace(0,np.nan),[cmdk,cntk],'운용대수 대비 적재OHT 비율')
   add(f,'stb_cmd',raw(d,'M16HUB.QUE.STB.3F_TO_M16A_3F_STB_CMD'),['M16HUB.QUE.STB.3F_TO_M16A_3F_STB_CMD'],'STB행 적재OHT 수')
   add(f,'zero',tm.eq(0).where(tm.notna()).rolling(3,min_periods=3).sum(),[tk],'최근3분 완료시간0 발생분수')
   cores[f]=pd.concat([q,tm,raw(d,cmdk),raw(d,cntk)],axis=1).notna().all(axis=1)
  for route,rq,alt,pk in ROUTES[f]:
   if rq:add(f,'route_'+route,raw(d,rq),[rq],route+'행 현재물량')
   if alt:add(f,'alt_'+route,raw(d,alt),[alt],route+'행 ALT대기')
   ps=raw(d,pk);add(f,'pio_'+route,ps.rolling(5,min_periods=5).sum(),[pk],route+'행 PIO 최근5분 합')
   add(f,'piofreq_'+route,ps.gt(0).where(ps.notna()).rolling(5,min_periods=5).sum(),[pk],route+'행 PIO 발생분수')
  if f=='M14A':
   for side in ['NORTH','SOUTH']:
    tk='M14.QUE.CNV.'+side+'M14TOCNVTIME1MIN';qk='M14.QUE.CNV.M14ATO'+side+'CURRENTQCNT'
    add(f,'cnvtime_'+side,raw(d,tk).where(raw(d,tk)>0).rolling(3,min_periods=2).median(),[tk],side+' CNV향 반송시간')
    add(f,'cnvq_'+side,raw(d,qk),[qk],side+' CNV향 물량')
  if f!='M16HUB':
   for typ,tail in [('normal','SORTERWAITCOUNTOVER'),('cu','CUSORTERWAITCOUNTOVER')]:
    k=p+'.SORTER.ABN.'+tail;add(f,'sorter_'+typ,raw(d,k).rolling(5,min_periods=3).median(),[k],typ+' Sorter대기 5분중앙값')
 return pd.DataFrame(z,index=d.index),spec,cores

def score(d,cfg):
 if cfg.get('version')!='1.2':raise ValueError('v1.2 engine requires v1.2 config; use history for v1.0')
 x,spec,cores=features(d);outputs=[]
 hub_storage=storage_context(d,cfg)
 def sev(k):
  p=cfg['parameters'].get(k)
  if not p or not p['enabled']:return pd.Series(np.nan,index=d.index)
  return ((x[k]-p['low'])/(p['high']-p['low'])).clip(0,1)
 def s(f,k):return sev(f+'.'+k)
 def available(s):return s.fillna(0) # unsupported component contributes nothing; cores/coverage separately exposed
 for f in FABS:
  delay=maximum(s(f,'time'),s(f,'sla'));q=s(f,'q');growth=s(f,'growth')
  deficit=s(f,'deficit');loss=s(f,'loss')
  backlog=maximum(.65*available(q)+.35*available(growth),minimum(growth,maximum(deficit,delay)))
  if f=='M16A':backlog=backlog*(.25+.75*maximum(available(delay),available(growth)*available(deficit)))
  portc=[];routesev={}
  for route,rq,alt,pk in ROUTES[f]:
   ps=s(f,'pio_'+route);freq=x[f+'.piofreq_'+route].ge(2)
   support=maximum(s(f,'route_'+route),s(f,'alt_'+route),delay,growth)
   val=ps.where(freq,0)*(.60+.40*available(support));routesev[route]=val;portc.append(val)
  port=maximum(*portc)
  if f=='M14A':
   cnv=maximum(*[minimum(s(f,'cnvtime_'+side),s(f,'cnvq_'+side)) for side in ['NORTH','SOUTH']])
   port=maximum(port,cnv)
   routesev['CNV구간']=cnv
  if f=='M16HUB':
   # Internal stock is measured independently; loaded ratio alone is not a failure.
   stop=pd.Series(0.,index=d.index)
   silent=x[f+'.zero'].ge(2).astype(float)*minimum(maximum(q,growth),s(f,'loaded')).fillna(0)
   impact=maximum(available(delay),available(port),available(silent))
   factor=cfg['hub_storage']['unconfirmed_fraction']+(1-cfg['hub_storage']['unconfirmed_fraction'])*impact
   queue_backlog=backlog*factor
   storage_backlog=available(hub_storage['severity'])*factor
   backlog=maximum(queue_backlog,storage_backlog)
  else:
   stop=minimum(loss,maximum(growth,deficit,delay))
   silent=pd.Series(0.,index=d.index)
  rapid=pd.Series(0.,index=d.index)
  if f!='M16HUB':
   ud=x[f+'.util_drop'];qj=x[f+'.qjump'];rc=cfg['rapid']
   fast=ud.ge(rc['util_drop_pp']) & qj.ge(rc['queue_jump_ratio'])
   strength=minimum(((ud-rc['util_drop_pp'])/12).clip(0,1),((qj-rc['queue_jump_ratio'])/.10).clip(0,1)).fillna(0)
   rapid=(rc['min_points']+(rc['max_points']-rc['min_points'])*strength).where(fast,0)
  comp=pd.DataFrame({'rapid':rapid,'delay':available(delay)*cfg['weights']['delay'],'backlog':available(backlog)*cfg['weights']['backlog'],'completion':available(stop)*cfg['weights']['completion'],'port':available(port)*cfg['weights']['port'],'silent':available(silent)*cfg['weights']['silent']})
  # Correlated proxies grouped above; do not add every indicator or route.
  ordered=np.sort(comp.to_numpy(),axis=1)[:,::-1]
  base=pd.Series(ordered[:,0]+.30*ordered[:,1]+.15*ordered[:,2],index=d.index).clip(0,100)
  acceleration=(base-base.shift(5)-15).clip(lower=0)*.25
  acceleration=acceleration.clip(upper=10).where(comp.ge(15).sum(axis=1)>=2,0).fillna(0)
  instant=(base+acceleration).clip(0,100)
  # 2-of-3 median filters isolated spikes; critical component may bypass median.
  smooth=instant.rolling(3,min_periods=2).median()
  smooth=maximum(smooth,instant.where((comp['completion']>=70)|(comp['rapid']>=40),0))
  valid=cores[f] & x[f+'.q'].shift(10).notna()
  scores=[];prev=None
  for v,ok in zip(smooth.to_numpy(),valid.to_numpy()):
   if not ok or not np.isfinite(v):scores.append(np.nan);prev=None
   else:
    v=float(v) if prev is None else max(float(v),prev-5.)
    scores.append(round(v,1));prev=v
  fs=pd.Series(scores,index=d.index);sortscore=pd.Series(np.nan,index=d.index)
  if f!='M16HUB':
   vals=[]
   for typ in ['normal']:
    sp=cfg['sorter_parameters'][f+'.sorter_'+typ]
    if sp['enabled']: vals.append(((x[f+'.sorter_'+typ]-sp['low'])/(sp['high']-sp['low'])*100).clip(0,100))
   sortscore=vals[0].round(1) if vals else pd.Series(np.nan,index=d.index)
  def state(v):
   return np.select([v.isna(),v>=70,v>=40,v>=20],['판단불가','위험','경고','주의'],default='낮음')
  top=comp.idxmax(axis=1).map(RULE_NAMES).where(comp.max(axis=1)>0,'뚜렷한 위험 신호 없음')
  top=top.where(valid,'필수값 결측 또는 초기 이력 부족')
  top=top.where(~(valid & fs.ge(20) & instant.lt(fs-1)), '회복 확인 중(하락 완화)')
  support_keys=[k for k,v in cfg['parameters'].items() if k.startswith(f+'.') and v['enabled']]
  coverage=x[support_keys].notna().mean(axis=1).mul(100).round(1)
  o=pd.DataFrame({'time':d.index,'FAB':f,'점수.FAB반송위험':fs.to_numpy(),'등급.FAB반송위험':state(fs),'점수.일반Sorter대기':sortscore.to_numpy(),'등급.일반Sorter대기':state(sortscore) if f!='M16HUB' else '해당없음','설명.주요위험':top.to_numpy(),'품질.필수입력유효':valid.to_numpy(),'품질.파생값관측률':coverage.to_numpy(),'점수.기본위험':base.round(2).to_numpy(),'점수.추세보정':acceleration.round(2).to_numpy()})
  for k in comp:o['룰.'+RULE_NAMES[k]]=comp[k].round(2).to_numpy()
  for k in ['q','growth','time','sla','loss','deficit','util_drop','qjump']:
   if f+'.'+k in x:o['파생.'+spec[f+'.'+k]['display'].split('.',2)[-1]]=x[f+'.'+k].round(4).to_numpy()
  for route,v in routesev.items():o['파생.'+route+'행Port위험']=v.round(4).to_numpy()
  o['룰버전']=cfg['version'];o['설정ID']=cfg['config_id']
  if f=='M16HUB':
   for col,key in [('원천.HUB 예약포함 저장률(%)','used'),('원천.HUB STB 빈공간 비율(%)','free'),('원천.HUB STB행 적재OHT 수','cmd'),('파생.HUB 예약포함 저장률 3분중앙값(%)','median'),('파생.HUB 저장률 기준이상 연속분수','minutes'),('파생.HUB 저장률 5분변화(%p)','delta'),('파생.HUB 저장대기 지속강도','severity'),('설명.HUB Storage 상태','state'),('품질.HUB 저장률 유효','valid')]:
    o[col]=hub_storage[key].to_numpy()
   o['파생.HUB 실제반송영향 강도']=impact.to_numpy()
   o['기여.HUB 내부JOB 대기']=queue_backlog.mul(cfg['weights']['backlog']).round(2).to_numpy()
   o['기여.HUB 예약포함 저장대기']=storage_backlog.mul(cfg['weights']['backlog']).round(2).to_numpy()
   o['설명.HUB 저장률 결측처리']=np.where(hub_storage['valid'],'','저장률 가점 제외; 나머지 관측값으로 판단')
  outputs.append(o)
 return pd.concat(outputs,ignore_index=True),x

def episodes(scores):
 result=[]
 for f,g in scores.groupby('FAB',sort=False):
  g=g.set_index('time');on=g['점수.FAB반송위험'].ge(40);ids=on.ne(on.shift()).cumsum()
  for _,z in g[on].groupby(ids[on]):
   result.append({'FAB':f,'start':str(z.index[0]),'last_above40':str(z.index[-1]),'duration_minutes':len(z),'peak':z['점수.FAB반송위험'].max(),'peak_time':str(z['점수.FAB반송위험'].idxmax()),'main_rule':z.loc[z['점수.FAB반송위험'].idxmax(),'설명.주요위험'],'label':'미확인 경보; 대화 부재만으로 오경보 판정 금지'})
 return pd.DataFrame(result)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);ap.add_argument('--fit',action='store_true');args=ap.parse_args()
 d,meta=load_data(args.input);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 if args.fit:
  raise ValueError('v1.2 frozen release: use a separately versioned calibration change, not --fit')
 else:cfg=json.loads(Path(args.config).read_text(encoding='utf-8'))
 result,x=score(d,cfg);result.to_csv(out/'FAB_scores.csv.gz',index=False,encoding='utf-8-sig',compression='gzip');episodes(result).to_csv(out/'alert_episodes.csv',index=False,encoding='utf-8-sig')
 summary=result.groupby('FAB').agg(valid=('점수.FAB반송위험','count'),median=('점수.FAB반송위험','median'),peak=('점수.FAB반송위험','max'),warning_minutes=('점수.FAB반송위험',lambda z:int(z.ge(40).sum())),critical_minutes=('점수.FAB반송위험',lambda z:int(z.ge(70).sum())))
 summary.to_csv(out/'score_summary.csv',encoding='utf-8-sig');print(summary.to_string());print('config_id',cfg['config_id'])
if __name__=='__main__':main()
