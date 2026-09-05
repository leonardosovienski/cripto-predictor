"""Integridade de encoding do registro científico e dos scripts do Windows.

Criado na auditoria de 2026-09-05, depois de um incidente real em cadeia:

1. `scripts/safe_pull.ps1` foi salvo em UTF-8 SEM BOM e continha travessões
   (`—`) dentro de strings. O Windows PowerShell 5.1 lê `.ps1` sem BOM como
   ANSI/cp1252, onde os 3 bytes do travessão viram `â€"` — e essa aspa final
   FECHA a string, quebrando o parser. O script nunca rodou na máquina de
   produção.
2. Como o `safe_pull.ps1` existia justamente para evitar stash/pull/pop manual
   no `trials.json` (PR #84), sua falha levou a resoluções de conflito à mão.
3. Uma dessas resoluções leu o `trials.json` como cp850 (codepage OEM do
   console) e regravou em UTF-8, corrompendo os travessões das notas para
   `ÔÇö` — mojibake silenciosa DENTRO do registro científico.

Um bug de encoding num utilitário virou corrupção do registro. Estes testes
travam os dois lados da cadeia.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TRIALS = REPO / "GarimpoInvestimentos" / "trials.json"

# Assinaturas de UTF-8 relido como cp850/cp1252, escritas com escapes de
# propósito: uma delas ("â€"") contém uma ASPA DUPLA literal —
# exatamente o que quebrou o parser do safe_pull.ps1 — e escrevê-la crua aqui
# reproduziria o bug neste próprio arquivo (aconteceu na primeira versão).
# ÔÇö = "ÔÇö", o travessão corrompido observado em produção.
MOJIBAKE = (
    "\u00d4\u00c7\u00f6",  # travessao lido como cp850 (o caso real, em trials.json)
    "\u00d4\u00c7\u00f4",  # meia-risca lida como cp850
    "\u00e2\u20ac\u0022",  # travessao lido como cp1252 - contem ASPA DUPLA
    "\u00c3\u00a9",  # e-agudo duplo-codificado
    "\u00c3\u00a7",  # c-cedilha duplo-codificado
    "\u00c3\u00a1",  # a-agudo duplo-codificado
)


def _ps1_files() -> list[Path]:
    return sorted((REPO / "scripts").glob("*.ps1"))


class TestScriptsPowerShell:
    def test_existem_scripts_para_verificar(self):
        """Guarda contra o teste virar vacuamente verde se os scripts sumirem."""
        assert _ps1_files(), "nenhum .ps1 encontrado em scripts/"

    @pytest.mark.parametrize("script", _ps1_files(), ids=lambda p: p.name)
    def test_ps1_e_ascii_puro_ou_tem_bom_utf8(self, script: Path):
        """PowerShell 5.1 lê `.ps1` sem BOM como ANSI. Um arquivo com qualquer
        byte não-ASCII e sem BOM é lido errado — e, se o caractere cair dentro
        de uma string, quebra o parser (foi o que aconteceu com safe_pull.ps1).
        Duas saídas seguras: ou o arquivo é ASCII puro, ou carrega BOM UTF-8."""
        raw = script.read_bytes()
        tem_bom = raw.startswith(b"\xef\xbb\xbf")
        corpo = raw[3:] if tem_bom else raw
        e_ascii = all(b < 0x80 for b in corpo)
        assert e_ascii or tem_bom, (
            f"{script.name}: contém bytes não-ASCII e NÃO tem BOM UTF-8 — "
            "o PowerShell 5.1 vai lê-lo como ANSI e pode quebrar o parser. "
            "Salve com BOM UTF-8 ou use só ASCII."
        )

    @pytest.mark.parametrize("script", _ps1_files(), ids=lambda p: p.name)
    def test_ps1_decodifica_como_utf8(self, script: Path):
        script.read_bytes().decode("utf-8")  # levanta se estiver corrompido


class TestRegistroCientifico:
    def test_trials_json_e_utf8_valido(self):
        TRIALS.read_bytes().decode("utf-8")

    def test_trials_json_sem_mojibake(self):
        """O registro é o artefato científico do projeto — texto corrompido nele
        é perda de informação, não cosmética."""
        texto = TRIALS.read_text(encoding="utf-8")
        achados = [m for m in MOJIBAKE if m in texto]
        assert not achados, (
            f"trials.json contém mojibake {achados} — sinal de que o arquivo foi "
            "lido com codepage ANSI/OEM e regravado. Restaure o texto correto e "
            "confira o fluxo que o reescreveu (resolução manual de conflito no "
            "Windows é a causa conhecida)."
        )

    def test_trials_json_sem_nomes_duplicados(self):
        """Reconciliar registros divergentes à mão pode duplicar entradas; o
        nome é a identidade da tentativa e tem que ser único."""
        nomes = [t["name"] for t in json.loads(TRIALS.read_text(encoding="utf-8"))]
        duplicados = {n for n in nomes if nomes.count(n) > 1}
        assert not duplicados, f"nomes duplicados em trials.json: {sorted(duplicados)}"

    def test_grade_de_thresholds_esta_registrada(self):
        """As 16 tentativas da varredura de 2026-09-04 rodaram em produção e
        ficaram só na máquina local até 2026-09-05 — o registro público
        subestimava a multiplicidade, e é dela que o Deflated Sharpe desconta.
        Este teste impede que elas sumam de novo numa resolução de conflito."""
        nomes = {t["name"] for t in json.loads(TRIALS.read_text(encoding="utf-8"))}
        grade = {n for n in nomes if n.startswith("v3-grid-btcusdt-")}
        assert len(grade) == 16, (
            f"esperadas 16 tentativas da varredura de threshold, encontradas {len(grade)}"
        )
