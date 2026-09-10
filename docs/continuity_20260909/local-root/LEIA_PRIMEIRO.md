# Cripto neste computador

A pasta de trabalho do projeto é **C:\Cripto**, incluindo todas as subpastas. Use o mapa atualizado em [CONFIGURACAO_LOCAL.md](pesquisa-20260909/docs/CONFIGURACAO_LOCAL.md).

- Código atualizado: `C:\Cripto\pesquisa-20260909`.
- Dados e ambientes congelados restaurados: `C:\Cripto\restaurado-20260908`.
- Configuração privada: `C:\Cripto\configuracao\pipeline.env`.
- Novos dados, saídas, logs, cache, estado e temporários: `C:\Cripto\operacao`.
- Relatórios e comprovantes: `C:\Cripto\operacao\relatorios`.

Para conferir a configuração sem consultar APIs:

```powershell
C:\Cripto\CRIPTO.cmd status
```

Para usar o ambiente Python e as ferramentas locais:

```powershell
C:\Cripto\CRIPTO.cmd pipeline --help
C:\Cripto\CRIPTO.cmd python -m scripts.diagnose_ar2_renewals --help
C:\Cripto\CRIPTO.cmd uv --version
```

Em 09/09/2026, o pipeline foi executado com mercado público, SerpAPI e Gemini; Groq também gerou resposta real. CoinGecko respondeu à verificação. Cerebras recusou geração com HTTP 402, sem pagamento. As chaves ficam somente na configuração privada; nenhuma credencial Binance foi usada. Os limites diários continuam ativos.

Leia [FECHAMENTO_PENDENCIAS_20260909.md](pesquisa-20260909/docs/FECHAMENTO_PENDENCIAS_20260909.md) para as correções, o mapa da arquitetura, os dados recuperados e as restrições. A base corrigida de futuros está em `operacao\dados\basis-recovered-20260909`; o banco operacional novo e as saídas estão em `operacao\saidas`.

**Próximo chat:** use a [versão final do prompt de revisão completa](pesquisa-20260909/docs/NEXT_CHAT_PROMPT.md), consolidada em 09/09/2026. Comece pelo que existe, estabeleça a nova linha de base e confronte as afirmações com código, testes e dados. Reavalie premissas e escolhas, confira fontes e lacunas e resolva as pendências em ciclos por fluxo. O documento preserva o estado das APIs e os limites autorizados e define critérios de prontidão por finalidade. Preparação técnica concluída não significa histórico completo nem lucro comprovado.

`LEIA-ME.md`, `RETOMAR_NO_CODEX.md`, o ZIP e os manifestos originais nesta raiz são arquivos preservados do pacote de migração. Seus caminhos antigos e instruções para uma máquina nova não são os destinos atuais. Não repita a restauração sobre esta instalação.

Nenhum agendamento, coleta recorrente ou operação financeira é ativado por essa configuração.

Para conferir o que existe e o que falta nos dados, leia [PRONTIDAO_DADOS.md](pesquisa-20260909/docs/PRONTIDAO_DADOS.md). Há verificações dos históricos, execução real concluída e limites explícitos de dados antigos, serviços e observação futura.

Fechamento técnico: 1.285 testes locais aprovados e um skip de symlink, 1.286 no CI com todos os extras, cobertura de execução de 89%. [Validação por commit](operacao/relatorios/FECHAMENTO_PENDENCIAS_20260909/VALIDACAO_FINAL.json).

[Atualização honesta para o investidor](operacao/relatorios/ATUALIZACAO_INVESTIDOR_20260909_FINAL.md).
