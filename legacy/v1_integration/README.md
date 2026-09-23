# Integração V1 (aposentada — D-13)

Testes de integração V1 que importam `cain` diretamente. Saíram da coleta
(`testpaths = ["tests"]`) na Fase 0 de qualificação (HYG-003): `cain-research`
não é dependência deste repositório na Etapa A. Ficam preservados como
referência para os testes da integração (Etapa B); não rodam no CI.

Qualificação Etapa A (missão crypto): `test_research_admission.py` e `test_research_results.py`
testavam a admission e o outbox do envelope V1 (`research_protocol`, HMAC do CAIN). O domínio
passou a ter contrato próprio sem envelope (`GarimpoInvestimentos/research_contract.py`); os
testes equivalentes estão em `tests/test_research_domain_units.py` e `tests/conformance/`.
Estes ficam preservados como referência para a Etapa B.
