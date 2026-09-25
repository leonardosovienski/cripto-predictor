#!/usr/bin/env bash
# Prompt 2, item 7: suíte do cripto-predictor como o CI roda (ci.yml: uv build + pytest --cov),
# isolada de rede (unshare -rn: namespace de rede vazio, loopback DOWN) e de segredos
# (env -i: ambiente vazio; HOME temporário vazio; nenhum .env na árvore).
set -uo pipefail
W=~/predictors/work/cripto-cripto-predictor          # worktree em 341d270 (árvore == HEAD 174573d do main)
VENV=~/predictors/runtime/cripto/venv                # criado por uv sync --locked --all-extras (uv.lock 9ab423a0…)
OUT=~/predictors/runtime/cripto/prompt2
H=$(mktemp -d -p ~/predictors/runtime/cripto)
cd "$W"
{
  echo "# $(date -u +%FT%TZ) HEAD=$(git rev-parse HEAD) tree=$(git rev-parse HEAD^{tree})"
  echo "# dist/ (uv build do mesmo commit): $(ls dist/ | tr '\n' ' ')"
  echo "# comando: env -i PATH=$VENV/bin:/usr/bin:/bin HOME=$H LANG=C.UTF-8 unshare -rn $VENV/bin/python -m pytest -p no:cacheprovider --cov=GarimpoInvestimentos --cov-report=term-missing --junitxml=$OUT/suite_isolated.junit.xml"
  echo "# rede no namespace: $(env -i PATH=/usr/bin:/bin unshare -rn python3 -c "import socket
s=socket.socket(); s.settimeout(3)
try: s.connect(('1.1.1.1',443)); print('ACESSÍVEL')
except OSError as e: print('bloqueada errno', e.errno)")"
} > "$OUT/suite_isolated.log"
start=$(date +%s)
env -i PATH="$VENV/bin:/usr/bin:/bin" HOME="$H" LANG=C.UTF-8 unshare -rn "$VENV/bin/python" -m pytest -p no:cacheprovider \
  --cov=GarimpoInvestimentos --cov-report=term-missing --junitxml="$OUT/suite_isolated.junit.xml" >> "$OUT/suite_isolated.log" 2>&1
echo "[exit $?] duração_s=$(( $(date +%s) - start ))" >> "$OUT/suite_isolated.log"
rm -rf "$H"
tail -3 "$OUT/suite_isolated.log"
