import datetime as dt
import json
import pathlib
import runpy
import socket
import sys
import time
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
sys.path.insert(0,str(REPO))
runpy.run_path(str(REPO/'tests/conftest.py'))
original_connect = socket.socket.connect
def denied(*args,**kwargs):
    if len(args)>1 and isinstance(args[1],tuple) and args[1][0] in ("127.0.0.1","::1"):
        return original_connect(*args,**kwargs)
    raise RuntimeError('Network disabled for selected offline tests')
socket.socket.connect=denied
socket.create_connection=denied
import pytest
args=['-q','-p','no:cacheprovider','--junitxml='+str(ROOT/'full_suite.xml'), 'tests']
started=dt.datetime.now(dt.UTC).isoformat()
t=time.perf_counter()
code=pytest.main(args)
(ROOT/'full_suite_receipt.json').write_text(json.dumps({'args':args,'started_at':started,'elapsed_seconds':time.perf_counter()-t,'exit_code':int(code),'scope':'Complete repository test suite; individual historical evidence tests included; external socket connect denied; loopback allowed for Windows asyncio; no new economic trial or frozen live evaluator execution'},indent=2),encoding='utf-8')
raise SystemExit(code)


