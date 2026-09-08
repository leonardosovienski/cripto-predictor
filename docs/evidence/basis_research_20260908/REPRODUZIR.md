# Reprodução da implementação BTC basis

O pacote `CRIPTO_BASIS_IMPLEMENTACAO.zip` contém o código desta rodada, os dados públicos preservados, todos os resultados concluídos, a execução parcial anterior, o diagnóstico público e as regras registradas.

## Ambiente

Execução validada com Python **3.13.14**, NumPy **2.5.1**, httpx **0.28.1** e pytest **8.4.2** para testes. O pacote não inclui o interpretador nem as bibliotecas. Com o ambiente já instalado, a reprodução dos dados salvos não faz consultas à internet.

Neste computador, o ambiente já disponível está em:

`C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2\.venv\Scripts\python.exe`

Para preparar outro ambiente, as dependências estão em `requirements.txt`. Sua instalação, se necessária, é uma etapa separada da reprodução offline. Não são necessárias credenciais ou contas de corretora.

## Reproduzir resultados, auditoria e planejamento com cotações salvas

Extraia o ZIP em uma pasta nova e abra um terminal na raiz extraída. Use o Python do ambiente acima ou outro ambiente com as mesmas versões:

```powershell
python -m scripts.reproduce_btc_basis --data data --expected results --diagnostic execution --output replay
```

A pasta `replay` precisa ser nova. O comando:

1. Verifica os hashes do código congelado, do protocolo e dos dados.
2. Reconstrói as 29 séries a partir das 532 respostas preservadas, incluindo checksums dos arquivos públicos.
3. Repete as duas regras nos três cenários registrados.
4. Exige identidade de bytes com os nove arquivos históricos de referência, além de gerar o manifesto de resultados.
5. Refaz a conta separada em Decimal e o plano de quantidades nas 12 amostras de livro preservadas.
6. Escreve `replay/reproduction_check.json`, com `status: PASS` quando todas as comparações passam.

O custo do cálculo contábil depende da máquina e pode levar alguns minutos. Os módulos de coleta pública não são chamados nesse processo.

## Testes do pacote

```powershell
python -m pytest tests/test_btc_basis.py tests/test_btc_execution_plan.py -q
```

São 28 testes novos. No repositório completo, passaram também 14 testes da rodada anterior, totalizando 42. Os módulos antigos necessários a esses 14 testes permanecem na entrega anterior e no repositório; não são duplicados neste pacote específico.

## Organização

| Caminho no pacote | Conteúdo |
|---|---|
| `scripts/` | Coleta, regras, auditoria, diagnóstico e reprodução |
| `tests/` | Testes desta implementação |
| `data/` | Respostas originais, checksums e séries normalizadas |
| `results/` | Resultado final v2 e seus hashes |
| `prior_partial_results/` | Arquivos v1 anteriores à correção do leitor de cenários |
| `execution/` | 26 respostas atuais, 12 amostras e os planos líquidos de BTC |
| `docs/evidence/basis_research_20260908/` | Pré-registro, congelamentos, correção e auditoria |
| `FILES_SHA256.json` | Integridade dos arquivos contidos no pacote |

Os coletores são ferramentas manuais de pesquisa pública. Eles não enviam ordens e não criam automações. A coleta de novas cotações não é necessária para reproduzir esta entrega e não modifica os resultados históricos.

O preço de liquidação publicado é um desfecho: só entra na conta às 08h UTC do vencimento, mesmo que a API rotule sua data à meia-noite. Dados posteriores ao corte não entram no desempenho. As classificações continuam históricas e adaptativas; um teste aprovado ou uma reprodução idêntica não certifica rentabilidade real.
