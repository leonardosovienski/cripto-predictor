# Incidente SerpAPI — registro local sanitizado

Estado: `BLOCKED_PENDING_SECRET_ROTATION`

O material recebido em 2026-08-01 afirma que uma credencial SerpAPI apareceu em cinco logs históricos. Esses logs não fazem parte do dump recebido; nenhum valor de credencial foi reproduzido ou registrado durante esta auditoria.

## Evidência e tratamento

- O dump original foi preservado fora do pacote de entrega e identificado por SHA-256 no manifesto de extração.
- A varredura do conteúdo recebido encontrou apenas expressões de código e fixtures sintéticas.
- Não havia `.env`, logs, SQLite, CSV, XLSX ou JSONL ativos no material recebido; por isso nenhuma evidência histórica foi apagada ou modificada.
- Logs presentes em outro host devem ser copiados para armazenamento restrito, receber hash SHA-256 e autorização humana antes de qualquer sanitização. A cópia original deve permanecer imutável.
- A redação estrutural foi incorporada ao pacote e o scanner local/CI não imprime valores encontrados.

## Ação humana obrigatória

A revogação/rotação da credencial no painel da SerpAPI e a verificação de uso indevido são ações externas e humanas. Mudanças locais não invalidam uma credencial já exposta. Até a confirmação documental dessa ação, o incidente permanece aberto e a credencial deve ser considerada comprometida.
