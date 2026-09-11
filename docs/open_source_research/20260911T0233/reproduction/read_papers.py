from pathlib import Path
import urllib.request,json,hashlib
from pypdf import PdfReader
root=Path(__file__).resolve().parents[1]
url='https://www.bis.org/publications/working-paper-1087-crypto-carry.pdf'
try:
 with urllib.request.urlopen(url,timeout=25) as r:data=r.read(12000001)
 if data.startswith(b'%PDF') and len(data)<=12000000:
  (root/'external/R41/full.pdf').write_bytes(data)
  (root/'external/R41/full_receipt.json').write_text(json.dumps({'url':url,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}))
except Exception as e:print('BIS',type(e).__name__)
for rid in ['R41','R42','R43','R44']:
 d=root/'external'/rid;p=d/('full.pdf' if rid=='R41' else 'paper.pdf')
 if not p.exists():continue
 try:
  reader=PdfReader(p)
  (d/'paper.txt').write_text('\n'.join(f'\nPAGE {i+1}\n'+page.extract_text() for i,page in enumerate(reader.pages)),encoding='utf-8')
  print(rid,len(reader.pages),'pages extracted')
 except Exception as e:print(rid,type(e).__name__)
