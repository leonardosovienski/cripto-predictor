import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('C:/Users/Superleo13/cripto-predictor')
WORK = Path(__file__).resolve().parent
files = [ROOT/p for p in subprocess.check_output(['git','ls-files','*.md'],cwd=ROOT,text=True).splitlines()]
issues = []
for path in files:
    name = path.relative_to(ROOT).as_posix()
    protected = name.startswith('docs/session_archive_') or name.startswith('docs/evidence/') and not name.startswith('docs/evidence/git_consolidation_')
    text = path.read_text(encoding='utf-8')
    fence = None
    visible = []
    for i,line in enumerate(text.splitlines(),1):
        stripped = re.sub(r'^(?:\s*>\s?)+','',line).lstrip()
        match = re.match(r'(`{3,}|~{3,})',stripped)
        if match:
            mark=match.group(1)
            if fence is None:
                fence=(mark[0],len(mark),i)
            elif mark[0]==fence[0] and len(mark)>=fence[1]:
                fence=None
            continue
        if fence is None:
            visible.append((i,line))
        if re.match(r'^(<{7}|={7}$|>{7})',line):
            issues.append(dict(file=name,line=i,issue='conflict_marker',protected=protected))
    if fence:
        issues.append(dict(file=name,line=fence[2],issue='unclosed_fence',protected=protected))
    for i,line in visible:
        for match in re.finditer(r'(?<!!)\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)',line):
            target=unquote(match.group(1).strip('<>'))
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target) or target.startswith(('#','/')):
                continue
            local=urlsplit(target).path
            if local and not (path.parent/local).exists():
                issues.append(dict(file=name,line=i,issue='missing_relative_target',target=target,protected=protected))
report={'tracked_markdown_files':len(files),'issues':issues}
(WORK/'markdown-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
