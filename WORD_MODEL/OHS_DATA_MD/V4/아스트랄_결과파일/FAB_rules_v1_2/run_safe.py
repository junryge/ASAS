"""Windows/Linux single-run wrapper. No retries. Timeout default 300 seconds."""
import argparse,subprocess,sys,json,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',default='result');p.add_argument('--timeout',type=int,default=300);a=p.parse_args()
 if not 10<=a.timeout<=3600:p.error('--timeout must be between 10 and 3600 seconds')
 root=Path(__file__).resolve().parent;out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 cmd=[sys.executable,str(root/'fab_risk_rules.py'),'--input',str(Path(a.input).resolve()),'--config',str(root/'rule_config.json'),'--out',str(out)]
 t=time.time()
 with (out/'run.log').open('w',encoding='utf-8') as log:
  try:
   x=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout,check=False);rc=x.returncode;state='completed' if rc==0 else 'failed'
  except subprocess.TimeoutExpired:rc=124;state='timeout'
 status={'status':state,'exit_code':rc,'elapsed_seconds':round(time.time()-t,2),'attempts':1,'automatic_retries':0}
 (out/'run_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(status,ensure_ascii=False));return rc
if __name__=='__main__':sys.exit(main())
