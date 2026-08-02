# Fontes de noticias — operacao e governanca

O modulo `GarimpoInvestimentos.collectors.news` separa a busca de noticias do
orquestrador da Fase 1. Cada ativo consulta uma fonte primaria, escolhida por hash
estavel do seu nome; as demais so sao tentadas quando a fonte primaria falha ou nao
retorna titulo pertinente. Nao se concatena conteudo de fontes diferentes na mesma
previsao.

## Provedores implementados

| Nome | Tipo | Credencial |
|---|---|---|
| `serpapi` | busca de noticias | `SERP_API_KEY` |
| `cryptopanic` | agregador cripto | `CRYPTOPANIC_AUTH_TOKEN` |
| `newsapi_ai` | Event Registry / NewsAPI.ai | `NEWSAPIAI_API_KEY` |
| `mediastack` | agregador de noticias | `MEDIASTACK_API_KEY` |
| `google_news_rss` | RSS de busca | nenhuma |
| `curated_rss` | uma fonte RSS cripto estavel por ativo | nenhuma |

`curated_rss` usa um subconjunto versionado do catalogo RSS ativo da CoinDesk Data
API: CoinDesk, Blockworks, Decrypt, Cointelegraph e CryptoPotato. A lista nao e
consultada durante uma rodada; qualquer troca de fonte e revisao de codigo e de
protocolo.

## Configuracao

O arquivo [`.env.example`](../GarimpoInvestimentos/.env.example) lista todas as
variaveis de credencial e configuracao do projeto. Copie-o para `.env` no mesmo
diretorio e preencha os valores localmente; o `.env` e ignorado pelo Git.

O padrao preserva a H5:

```dotenv
NEWS_PROVIDERS=serpapi
```

Uma futura trial forward pode optar, por exemplo, por:

```dotenv
NEWS_PROVIDERS=serpapi,cryptopanic,google_news_rss,curated_rss
CRYPTOPANIC_AUTH_TOKEN=<valor fora do Git>
```

Para distribuir os ativos por todas as fontes alternativas e deixar apenas uma
fonte de reserva, configure as primarias em `NEWS_PROVIDERS` e a reserva separada:

```dotenv
NEWS_PROVIDERS=cryptopanic,newsapi_ai,mediastack,google_news_rss,curated_rss
NEWS_FALLBACK_PROVIDER=serpapi
```

Nesse perfil cada ativo recebe uma primaria deterministica entre as cinco; somente
falha, resposta vazia ou circuit breaker faz o router consultar a SerpAPI. A
politica completa, incluindo o fallback, e gravada na provenance da previsao.

`newsapi_ai` e `mediastack` tambem sao opt-in e consomem as respectivas quotas.
Para reduzir exposicao, o primeiro envia a chave no corpo de uma requisicao POST;
o segundo exige query-string por contrato do provedor, portanto o cliente nunca
deve registrar URL, parametros ou resposta bruta. Ative-os apenas em uma nova
trial forward, com `API_GUARD_ENABLED=true` e um teto de tentativas adequado ao
plano contratado.

O router abre um circuit breaker somente para 429 e 5xx. Depois disso, essa fonte
e ignorada ate o proximo processo/rodada, evitando retries repetidos por ativo.

## Carimbo de previsao

A migracao `0010_predictions_news_provenance` adiciona `news_provider` e
`news_degraded_reason` as previsoes. Linhas anteriores ficam `NULL`: elas nao sao
reinterpretadas como tendo usado uma fonte nova. A ausencia completa de noticia
continua marcada por `input_degradado=1`.

## Regra cientifica

Mudar `NEWS_PROVIDERS`, URLs curadas, roteamento ou forma de busca muda o input
do LLM. Logo, nao se ativa essa configuracao dentro da H5: registrar uma nova
trial e coletar uma amostra forward separada e obrigatorio.


