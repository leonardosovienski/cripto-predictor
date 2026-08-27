# Gate obrigatorio para a proxima trial

Este documento nao abre nem nomeia uma trial. Ele registra as condicoes minimas
que devem ser preenchidas antes do proximo `registered_at`.

- usar identificador livre; H7 ja pertence a macro/DXY;
- excluir toda previsao anterior ao novo `registered_at`;
- declarar familia e parentesco com as tentativas anteriores;
- congelar efeito minimo relevante, poder desejado e `n` calculado;
- declarar autocorrelacao, overlap D+7 e regra de multiplicidade/DSR;
- escolher antes da coleta um juiz fixo, meta-analise pre-especificada ou
  replicacao obrigatoria entre juizes;
- publicar `n`, efeito e intervalo por juiz mesmo quando o gate for agregado;
- proibir a regra "vence se qualquer juiz passar";
- incluir provider, modelo, prompt hash, horizonte, thresholds, fonte de preco,
  politica de custo e versoes das wheels no `pipeline_fingerprint`;
- definir tratamento de gaps, perda de banco, restauracao de backup e dados
  degradados antes da primeira observacao;
- exigir fonte de preco paralela com comparacao de timestamp/candle e politica
  de quarentena para divergencia;
- manter `capital_authorized=false` ate veredito prospectivo liquido de custos.

H6 permanece inalterada. Estratificacao decisoria nova, recuperacao seletiva de
dados ou mudanca de gate exigem trial prospectiva separada.
