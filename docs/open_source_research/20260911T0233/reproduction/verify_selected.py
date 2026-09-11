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
def denied(*args,**kwargs):
    raise RuntimeError('Network disabled for selected offline tests')
socket.socket.connect=denied
socket.create_connection=denied
import pytest
args=['-q','-p','no:cacheprovider','--junitxml='+str(ROOT/'selected_tests.xml'), 'tests/test_dpl.py','tests/test_pbo.py','tests/test_v3_costs.py','tests/test_audit_economic_accounting.py']
started=dt.datetime.now(dt.UTC).isoformat()
t=time.perf_counter()
code=pytest.main(args)
(ROOT/'selected_tests_receipt.json').write_text(json.dumps({'args':args,'started_at':started,'elapsed_seconds':time.perf_counter()-t,'exit_code':int(code),'scope':'Synthetic selected tests only; socket connect denied; no full-suite or frozen market evaluation claim'},indent=2),encoding='utf-8')
raise SystemExit(code)
