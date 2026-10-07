from pathlib import Path
import argparse,json,zipfile,hashlib
import pandas as pd,numpy as np
from fab_risk_rules import load_data,score,features,FABS
R=Path(__file__).resolve().parent

def main(path):
 d,_=load_data(path);c=json.loads((R/'rule_config.json').read_text());checks=[]
 def ck(name,ok):
  if not bool(ok):raise AssertionError(name)
  checks.append({'check':name,'passed':True})
 n=pd.read_csv(R/'design_replay/FAB_scores.csv.gz',low_memory=False,parse_dates=['time'])
 with zipfile.ZipFile(R/'history/FAB_위험룰_v1_1_실행패키지.zip') as z:
  with z.open('FAB_rules_v1_1/design_replay/FAB_scores.csv.gz') as f:o=pd.read_csv(f,compression='gzip',low_memory=False,parse_dates=['time'])
 for fab in FABS:
  a=o[o.FAB.eq(fab)].set_index('time');b=n[n.FAB.eq(fab)].set_index('time')
  ck(fab+' FAB 반송위험은 모든 분에서 v1.1과 동일',a['점수.FAB반송위험'].equals(b['점수.FAB반송위험']))
  if fab!='M16HUB':
   p=c['sorter_parameters'][fab+'.sorter_normal'];col=c['features'][fab+'.sorter_normal']['raw_columns'][0]
   expected=((d[col].rolling(5,min_periods=3).median()-p['low'])/(p['high']-p['low'])*100).clip(0,100).round(1)
   ck(fab+' 일반 Sorter 원천 하나로 직접 계산한 결과 일치',np.allclose(b['점수.일반Sorter대기'],expected,equal_nan=True))
  else:ck('HUB 일반 Sorter 미평가',b['점수.일반Sorter대기'].isna().all())
 small=d.loc['2026-08-26'].copy();base,_=score(small,c);changed=small.copy();changed[[k for k in d if 'CUSORTER' in k]]=1000000;altered,_=score(changed,c)
 ck('CU Sorter 급증은 일반 Sorter 및 FAB 반송점수에 영향 없음',base[['점수.FAB반송위험','점수.일반Sorter대기']].equals(altered[['점수.FAB반송위험','점수.일반Sorter대기']]))
 ck('모든 CU Sorter 비활성',all(not v['enabled'] for k,v in c['sorter_parameters'].items() if k.endswith('sorter_cu')))
 ck('일반 Sorter 점수 범위',n['점수.일반Sorter대기'].dropna().between(0,100).all())
 (R/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(json.dumps({'passed':len(checks),'failed':0}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);main(p.parse_args().input)
