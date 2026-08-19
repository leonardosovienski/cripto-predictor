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

Essas duas ações continuam como `EXTERNAL_BLOCKER` para fins de auditoria formal — mas não bloqueiam mais o funcionamento do pipeline, que já está operando com as chaves novas (confirmado pelo próprio dono em produção).
