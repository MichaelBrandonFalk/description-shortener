"""Exercise the packaged native helper on its actual target OS, without user data."""
import json,os,subprocess,sys,tempfile,time,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from engine import hard_errors
resources=Path(sys.argv[1]);helper=resources/'helper'/('shortener-helper.exe' if os.name=='nt' else 'shortener-helper')
p=subprocess.Popen([str(helper),str(resources),'--serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env={**os.environ,'DESCRIPTION_SHORTENER_BACKEND':'cpu'})
def request(data):
    started=time.monotonic();p.stdin.write(json.dumps(data)+'\n');p.stdin.flush()
    while True:
        line=p.stdout.readline()
        if not line:raise RuntimeError('The packaged helper stopped: '+p.stderr.read()[-1000:])
        event=json.loads(line)
        if event['event'] in ('ready','result'):
            if not event['ok']:raise AssertionError(event)
            print(json.dumps({'request':data['request_id'],'seconds':round(time.monotonic()-started,2),'backend':event.get('backend'),'counts':event.get('counts')}),flush=True)
            return event
try:
    assert request({'mode':'warm','request_id':'warm'})['backend']=='cpu'
    cases=json.loads((ROOT/'benchmarks/cases.json').read_text())
    # Generation, material detail retention, planned action, and numeric/negation checks.
    for case in cases:
        result=request({'mode':'text','text':case['description'],'character_limit':110,'request_id':case['id']})
        text=result['text'];assert not hard_errors(case['description'],text)
        import re
        assert all(re.search(pattern,text,re.I) for pattern in case['required']), (case['id'],text)
        assert not any(re.search(pattern,text,re.I) for pattern in case['forbidden']), (case['id'],text)
    bottle=cases[1]['description']
    assert request({'mode':'text','text':bottle,'character_limit':150,'request_id':'higher-limit'})['text']==bottle
    assert len(request({'mode':'text','text':bottle,'character_limit':110,'request_id':'reset-limit'})['text'])<=110
    with tempfile.TemporaryDirectory(prefix='description-shortener-smoke-') as temp:
        source=Path(temp)/'input.csv';destination=Path(temp)/'output.csv'
        with source.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f,delimiter=';');writer.writerow(['SKU','Description','Price']);writer.writerow(['001',bottle,'12.90'])
        before=source.read_bytes();request({'mode':'file','source':str(source),'destination':str(destination),'character_limit':110,'request_id':'csv'})
        assert source.read_bytes()==before
        with destination.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f,delimiter=';'))
        assert rows[1][0]=='001' and rows[1][2]=='12.90' and len(rows[1][1])<=110
finally:
    p.stdin.close();p.wait(timeout=30)
print('Packaged CPU model: 11 cases, limit changes, cache isolation, file output and clean shutdown passed.',flush=True)
