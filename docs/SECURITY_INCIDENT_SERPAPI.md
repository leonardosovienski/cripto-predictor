# Incidente SerpAPI — registro local sanitizado

Estado: `ROTATED_CONFIRMED_BY_OWNER_2026-08-19` (rotação confirmada; verificação de uso indevido no painel do provedor segue como ação externa não observável a partir deste repositório)

O material recebido em 2026-08-01 afirma que uma credencial SerpAPI apareceu em cinco logs históricos. Esses logs não fazem parte do dump recebido; nenhum valor de credencial foi reproduzido ou registrado durante esta auditoria.

## Evidência e tratamento

- O dump original foi preservado fora do pacote de entrega e identificado por SHA-256 no manifesto de extração.
- A varredura do conteúdo recebido encontrou apenas expressões de código e fixtures sintéticas.
- Não havia `.env`, logs, SQLite, CSV, XLSX ou JSONL ativos no material recebido; por isso nenhuma evidência histórica foi apagada ou modificada.
- Logs presentes em outro host devem ser copiados para armazenamento restrito, receber hash SHA-256 e autorização humana antes de qualquer sanitização. A cópia original deve permanecer imutável.
- A redação estrutural foi incorporada ao pacote e o scanner local/CI não imprime valores encontrados.

## Ação humana obrigatória (histórico — preservado sem reescrita; estado original: `BLOCKED_PENDING_SECRET_ROTATION`)

A revogação/rotação da credencial no painel da SerpAPI e a verificação de uso indevido são ações externas e humanas. Mudanças locais não invalidam uma credencial já exposta. Até a confirmação documental dessa ação, o incidente permanece aberto e a credencial deve ser considerada comprometida.

## Rotação confirmada — 2026-08-19

O proprietário do repositório confirmou diretamente, em sessão de auditoria, ter rotacionado as 5 credenciais que haviam sido expostas em texto puro durante depuração ao vivo desta mesma auditoria (`GEMINI_API_KEY`, `SERP_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`). Esta confirmação é textual/verbal do próprio dono do projeto, não uma evidência criptográfica verificável a partir deste repositório — por isso o estado registra `ROTATED_CONFIRMED_BY_OWNER`, não `RESOLVED`/`CLOSED`.

Duas coisas permanecem fora do escopo verificável por este código:
- Confirmação, no painel de cada provedor, de que as chaves antigas foram de fato revogadas (não apenas que novas foram geradas).
- Verificação de uso indevido das chaves antigas antes da rotação.

Essas duas ações continuam como `EXTERNAL_BLOCKER` para fins de auditoria formal — mas não bloqueiam mais o funcionamento do pipeline, que já está operando com as chaves novas (confirmado pelo próprio dono em produção). Já rastreadas em `docs/OVERVIEW_E_ROADMAP_2026-08-21.md` e `docs/PANORAMA_2026-08-21.md` ("Verificar a revogação das chaves antigas do SerpAPI", sem prazo) — este documento não abre uma pendência nova, só concentra o estado.

## Integridade dos inputs da H5 na janela de exposição — discussão registrada em 2026-08-24

Pergunta em aberto desde o incidente, nunca respondida por escrito: a H5
(`v2-dpl-multi-h7`, coletada 2026-07-10 a 2026-07-28, REFUTADA/NO-GO em
2026-07-28) usou notícias via SerpAPI como parte do input do juiz LLM. Se a
credencial esteve comprometida DURANTE essa janela, os inputs de H5 seriam
confiáveis?

**Não dá para responder com certeza — e por dois motivos diferentes, que não
devem ser confundidos.**

1. **A data exata da exposição é desconhecida por desenho.** O material de
   2026-08-01 afirma que a credencial apareceu em cinco logs históricos, mas
   a regra #8 deste projeto (`docs/OVERVIEW_E_ROADMAP_2026-08-21.md`) proíbe
   abrir esses logs em texto bruto — corretamente, para não espalhar mais a
   credencial exposta. Isso significa que este repositório **nunca vai
   conseguir confirmar** se a janela de exposição real se sobrepõe à janela
   de coleta de H5 (10 a 28/07). Não é uma lacuna a preencher; é uma
   consequência aceita da própria mitigação — a alternativa (abrir os logs
   para checar a data) reintroduziria o risco que a política existe para
   evitar.

2. **Mesmo que se soubesse a data, o dado bruto para reauditar não existe
   mais.** `phase1.py`/`main.py` só persistem `input_degradado` (0/1),
   `news_provider` e `news_degraded_reason` por previsão — o TEXTO das
   notícias (`news_result.titles`) é usado para montar o prompt do LLM e
   descartado, nunca gravado na Feature Store. Não há como reexaminar hoje
   se uma notícia específica, usada numa previsão específica de H5, foi
   manipulada ou legítima. Este é um fato estrutural sobre o pipeline, não
   uma perda causada pelo incidente — o mesmo valeria para qualquer previsão
   antiga, exposição ou não.

**O que isso muda no veredito de H5 (nada) e por quê.** Uma credencial
exposta em log permite que TERCEIROS façam consultas usando-a (risco de
cota/custo/rate-limit) — isso não implica que as RESPOSTAS recebidas pelo
pipeline de coleta legítimo tenham sido alteradas; isso exigiria um ataque
ativo (MITM) na conexão HTTPS com a SerpAPI, uma categoria de ameaça
diferente e sem qualquer evidência levantada nesta auditoria. Mesmo sob a
leitura mais cautelosa possível — supor que a coleta de H5 caiu dentro da
janela de exposição E que isso degradou a qualidade das notícias recebidas
— o efeito plausível é MAIS previsões com `input_degradado=1`, uma variável
que H5 já rastreia e já estratificou: 47,3% completo vs 52,7% degradado
(`docs/H5_ACOMPANHAMENTO_2026-07-25.md`). A nota de veredito em
`trials.json` (`v2-dpl-multi-h7`) já registrou, por honestidade, que nem o
estrato de input completo nem o degradado isoladamente atingem
significância — o resultado POOLED (que decide o critério pré-registrado) é
negativo em ambos os estratos, e não há mecanismo plausível pelo qual
degradar notícias FABRICARIA uma correlação negativa direcional. **O
veredito de H5 permanece REFUTADA/NO-GO sem depender desta questão.**
