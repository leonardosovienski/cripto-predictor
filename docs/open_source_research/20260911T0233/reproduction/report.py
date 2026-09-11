import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
DOC=REPO/'docs/open_source_research/20260911T0233'
DOC.mkdir(parents=True,exist_ok=True)
baseline=json.loads((ROOT/'baseline.json').read_text(encoding='utf-8'))
bench=json.loads((ROOT/'benchmark_result.json').read_text(encoding='utf-8'))
rows=json.loads((ROOT/'candidates.json').read_text(encoding='utf-8'))+json.loads((ROOT/'extra_candidates.json').read_text(encoding='utf-8'))
deep=json.loads((ROOT/'deep_sources.json').read_text(encoding='utf-8'))
SHA=baseline['head']

def table(headers,rows):
    def cell(v): return str(v).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(cell(v) for v in r)+' |\n' for r in rows)

def link(path,line=1):
    return f'[{path}:{line}](https://github.com/leonardosovienski/cripto-predictor/blob/{SHA}/{path}#L{line})'

# These are per-claim reviews, not whole-repository certifications.
NOTES={
'R01':('C2','lookahead.py:66–95; test_lookahead_analysis.py:23–88; docs/lookahead-analysis.md','Compara indicadores nas mesmas linhas de execuções completas e truncadas. Os testes lidos verificam acionamento e configuração inválida, não toda sensibilidade do detector.','Usar o desenho de comparação por prefixos como diagnóstico; sinais não acionados podem escapar e rankings entre pares podem produzir falsos positivos.','K02 K05'),
'R02':('C2','arbitrage_executor.py:28–48,123–141,215–264; test_arbitrage_executor.py:48–87','Há cálculo de custos das duas pernas e preços normalizados por conversão. A elegibilidade considera tokens com USD no nome intercambiáveis; o teste aceita ETH-BUSD versus ETH-USDT.','Adapter restrito para comparação de contabilidade. Não importar a elegibilidade como prova de paridade, liquidez de conversão ou financiamento das duas pernas.','K06 K07'),
'R05':('C1','exchange.py:4969–4990,5182–5192; Manual.md, seção OHLCV','A base normaliza seis campos OHLCV e recusa métodos não suportados. Suporte uniforme da interface não demonstra suporte em toda venue. No projeto, CCXT 4.5.70 já está instalado.','KEEP; validar semântica por exchange e produto. O provider local descarta candle aberto, mas fechamento convencional não é recibo real de publicação histórica.','K01 K07'),
'R07':('C1','queue.rs:63–138; latency.rs localizado; documentação Order Fill','O modelo conservador inicializa quantidade à frente, reduz com trades e limita pela profundidade; modelos probabilísticos representam incerteza de fila.','AUGMENT no estudo de fills com limites. Replay não altera o mercado; capacidade e impacto continuam fora da verificação. Não instalar para simular latência institucional local.','K06'),
'R08':('C1','binance.py:334–413','Book mantém quantidades Decimal, trata remoção de níveis e transmite sequência, horário do evento, recepção e bruto; chama validação de update ID. Funding inclui próximo horário, não apenas pagamento realizado.','Candidato a feed delimitado de microestrutura. Preservar distinção event/receipt e funding estimado/liquidado; teste de Binance procurado retornou 404, não se infere ausência de testes.','K01 K06 K07'),
'R09':('C1','src/adaptors/aave-v3/index.js:61–101,155–243; README.md','Adapter consulta reservas/configuração, exclui congeladas, distingue caixa, dívida e oferta; apyBase nessa seção é liquidityRate/RAY ×100.','Útil para discovery; não equivale a rendimento realizado composto. Exclusão corrente de reservas não reconstrói universo passado. Renda do estudo local usa razão de índices, que é outro objeto.','K03 K12'),
'R10':('C1','ReserveLogic.sol, getNormalizedIncome; MathUtils.sol:1–37','Juro linear entre atualizações usa segundos/365 dias em RAY. O coletor local reconstrói normalized income e arredondamento; a referência aave-v3-core está arquivada desde a fotografia da API.','VALIDATE, sem tratar o repositório arquivado como implementação atual do proxy no bloco histórico. Corroborar implementação/endereço/bloco e segunda rota RPC. SPDX BUSL-1.1 no arquivo exige análise separada para reuso.','K03'),
'R11':('C2','SwapMath.sol:21–96; test/SwapMath.spec.ts:20–80','Swap por etapa trata exact-in/exact-out, limite de preço e arredondamento de fees. Testes conferem quantidades exatas e que a etapa não consome toda a ordem quando atinge alvo.','Referência de cálculo, não estimador de lucro de LP. Precisa ticks, liquidez ativa, custos de reposicionamento e seleção adversa; adiar estratégia até dados e protocolo.','K13'),
'R22':('C2','src/alphalens/performance.py:28–85; tests/test_performance.py:114–138','IC é Spearman por data e ativos, com opção de ajuste por grupo; teste compara DataFrame esperado. Importa SciPy, pandas e outras bibliotecas.','AUGMENT ranking, IC por data, turnover e exposição. É descendente de Alphalens, não réplica de linhagem independente; SciPy compartilhado reduz independência do cálculo. Calendário e perdas de ativos precisam contrato cripto.','K04'),
'R25':('C1','multiple_comparison.py:501–565,635–709','SPA trabalha com perdas benchmark e alternativas, bootstrap em blocos e três centramentos; calcula distribuição do máximo e p-values.','Complemento ao PBO/DSR, não substituição automática. Exige matriz de perdas comparáveis e registro de todas as tentativas. Tamanho de bloco default não é justificativa científica. Testes baixados, sem revisão de suas asserções nesta rodada.','K05'),
'R26':('C1','_stattools.py:2681–2717','Cointegração ajusta OLS e ADF dos resíduos; alerta para colinearidade quase perfeita e usa valores críticos apropriados ao desenho.','Candidato para resíduos/pares; ajuste e escolha da janela devem ocorrer dentro de treino. Teste de cointegração não prova spread executável, hedge disponível ou retorno após borrow.','K10'),
'R27':('C2','_split.py:1292–1327; test_split.py:1869–1907','TimeSeriesSplit separa teste e treino com gap de contagem de linhas e limite opcional de treino; testes verificam índices exatos.','VALIDATE fronteiras. Gap por linha não equivale a purging por término do label quando horizontes variam; não elimina seleção externa ao split. Já instalado no projeto.','K05'),
'R28':('C2','_combinatorial.py:329–362; test_combinatorial.py:26–89','Matriz de folds marca purga antes/depois e embargo; testes verificam índices com e sem purga.','Referência para testar fronteiras. Caminhos combinatórios podem treinar em datas posteriores ao teste; não são automaticamente simulação causal de implantação ou amostras independentes.','K05 K11'),
'R39':('C1','blackformula.cpp:59–106; test-suite/blackformula.cpp:36–69','Black valida desvio padrão e desconto, com caso de volatilidade zero. Teste inspecionado cobre round-trip de volatilidade implícita Bachelier; não certifica toda fórmula Black.','Referência parcial para opções/Greeks. Falta contrato de quote, settlement, IV e liquidez histórica do instrumento cripto; não pressupor payoff linear em USD.','K14'),
'R52':('C4','SciPy instalado stats/_stats_py.py:5401–5465; benchmark_result.json','Spearman usa rankdata e correlação, sinaliza entradas constantes. A comparação local B01 conferiu 100 casos sintéticos com empates; B02 usou NumPy para SMA/Bollinger.','KEEP implementações locais no escopo aprovado; referências complementam diagnóstico. Alphalens usa SciPy, portanto não acrescenta uma terceira linhagem independente para essa mesma conta.','K02 K04'),
}

CAPS='''K01|Identidade, relógios e universo PIT|SCIENTIFIC_ENABLER|PARCIAL|C1|IMPROVE|CANDIDATE|R05 R08 R20 R47 R48 R50|GarimpoInvestimentos/dpl/providers/ccxt_base.py:80|Distinguir fechamento convencionado, publicação comprovada e recepção; preservar ativos retirados e contratos|Dados brutos versionados por fonte, chain/venue/settlement e universo por data|Sem isso, cobertura e seleção podem ser confundidas com alpha
K02|Referências diferenciais para métricas e features|ENGINEERING|IMPLEMENTADO|C4|VALIDATE|CANDIDATE|R01 R27 R52|GarimpoInvestimentos/analyzers/indicators.py:26|Detectar erro numérico e dependência do futuro antes de comparar estratégias|Sintético e ambiente existente; 100 pares e 231 prefixos executados|Não testa RSI/MACD/HMM completo, nem poder do bootstrap
K03|Corroboração dos índices Aave e liquidez de saída|SCIENTIFIC_ENABLER|PARCIAL|C1|VALIDATE|BLOCKED_DATA|R09 R10 R48|scripts/recover_aave_history.py:154|Verificar que rendimento histórico vem de índices do contrato correto, não APY anunciado|Mesmos blocos, hashes, reserva USDC nativa, implementação histórica e rota RPC adicional|Mesma cadeia ou backend não são amostras econômicas independentes
K04|Ranking cross-sectional com neutralização e turnover|ECONOMIC_STRATEGY|PARCIAL|C1|AUGMENT|BLOCKED_DATA|R22 R42 R52|GarimpoInvestimentos/collectors/discovery.py:88|Investigar momentum/resíduos além da seleção heurística atual, separando beta e custo|Painel por data com delistings, volumes/custos e elegibilidade histórica|IC positivo não garante PnL; Alphalens não é independente de SciPy
K05|Validação temporal e multiplicidade do processo inteiro|SCIENTIFIC_ENABLER|PARCIAL|C3|AUGMENT|CANDIDATE|R01 R25 R27 R28 R43|GarimpoInvestimentos/analyzers/pbo.py:100|Combinar verificações de fronteira com perdas comparáveis e todas as tentativas|Labels com início/fim, lista de variantes, matriz de perdas e desenho de blocos|PBO existente não deve ser reconstruído; CPCV não implica causalidade operacional
K06|Replay de fills, fila, atraso e duas pernas|SCIENTIFIC_ENABLER|PARCIAL|C1|AUGMENT|BLOCKED_DATA|R02 R03 R07 R08|scripts/plan_btc_hedge_v3.py:20|Estimar intervalo de resultado quando posição de fila e simultaneidade não são conhecidas|L2 sequenciado, trades, clocks e cenários de latência/capital|Snapshots atuais não identificam fila; replay não modela impacto próprio
K07|Instrumentos e funding como eventos assinados|SCIENTIFIC_ENABLER|PARCIAL|C3|IMPROVE|CANDIDATE|R05 R08 R20 R45|GarimpoInvestimentos/v3/backtest_v3.py:322|Separar taxa projetada de cada pagamento e evitar convenções universais de 8h|Identificador de contrato, eventos, mark, intervalo histórico e margem|Não reparametrizar custos das famílias encerradas
K08|Vintages macro e calendário conhecido no instante|SCIENTIFIC_ENABLER|PARCIAL|C1|AUGMENT|BLOCKED_DATA|R50|GarimpoInvestimentos/dpl/providers/dxy.py:55|Permitir avaliação causal da informação macro sem backfill conhecido apenas hoje|ALFRED/release preservado com intervalo de versão e hora de publicação|DXY é nome interno; DTWEXBGS não deve ser confundido com todo índice dólar
K09|Eventos, notícias e extração com LLM|SCIENTIFIC_ENABLER|EXPERIMENTAL|C1|VALIDATE|DEFER|R49 R53|GarimpoInvestimentos/dpl/snapshots.py:97|Testar extração/classificação antes de tratar score como probabilidade ou sinal|Publicação, recibo, texto preservável, versão/prompt; protocolo pareado v3 já registrado|Janelas futuras e H5 sem inputs não podem ser preenchidos retroativamente
K10|Pares, resíduos e fatores de risco|ECONOMIC_STRATEGY|DESCONHECIDO|C0|RESEARCH|BLOCKED_DATA|R26 R42|GarimpoInvestimentos/collectors/discovery.py:88|Investigar prêmio de risco/valor relativo com hedge e borrow explícitos|Painel PIT e hedge negociável com financiamento|Correlação/cointegração não garantem convergência nem liquidez
K11|Carteira, concentração e alocação de garantias|SCIENTIFIC_ENABLER|PARCIAL|C1|AUGMENT|CANDIDATE|R28 R29 R30|GarimpoInvestimentos/profit_research.py:80|Distinguir retorno sobre margem de retorno sobre todo capital e não somar cenários|Equity, caixa por venue/colateral, exposições e cenários de cauda|Custos pessoais e elegibilidade são desconhecidos
K12|Lending/staking com taxas realizadas e stress|ECONOMIC_STRATEGY|EXPERIMENTAL|C1|AUGMENT|BLOCKED_DATA|R09 R10 R13 R14 R15 R51|scripts/recover_aave_history.py:154|Investigar remuneração de empréstimo/validação de rede descontando saídas e riscos|Índices e fluxos realizados, resgate, gas, slashing, depeg e custos|Histórico Aave documentado é condicional; não reproduzido nesta rodada
K13|LP concentrada e seleção adversa|ECONOMIC_STRATEGY|DESCONHECIDO|C0|RESEARCH|BLOCKED_DATA|R11 R12 R44|scripts/plan_btc_hedge_v3.py:55|Investigar fees menos perdas relativas, custos e reposicionamento|Ticks, swaps, liquidez ativa, gas e benchmark de rebalanceamento|Mais receita de fees não prova lucro; LVR é comparação contra benchmark específico
K14|Opções, superfície IV, skew e Greeks|ECONOMIC_STRATEGY|DESCONHECIDO|C0|RESEARCH|BLOCKED_DATA|R39 R46|pyproject.toml:16|Separar prêmio de volatilidade de erro de preço e risco de cauda|Cadeia histórica bid/ask, expiração, settlement, funding de hedge|Sem histórico admissível; cálculo teórico não comprova fill
K15|Fluxos on-chain, entidades e stablecoins|SCIENTIFIC_ENABLER|DESCONHECIDO|C0|RESEARCH|BLOCKED_DATA|R16 R17 R18 R47 R48 R49|GarimpoInvestimentos/dpl/signals.py:1|Distinguir movimento econômico de revisão retrospectiva de rótulos|Bloco finalizado, data do indexador e vintage de classificação de entidade|Métrica atual reconstruída pode carregar informação futura
K16|Baselines probabilísticos e modelos de estado|SCIENTIFIC_ENABLER|EXPERIMENTAL|C1|VALIDATE|DEFER|R26 R27 R34 R35 R37|GarimpoInvestimentos/v3/regime_engine.py:298|Comparar regra simples, linear e probabilístico pela decisão e calibração|Treino separado, target fixo, incerteza e erro por regime|HMM existente não autoriza reabrir família funding_oi_hmm_v3
K17|Transformers, ensembles e RL|ECONOMIC_STRATEGY|DESCONHECIDO|C0|RESEARCH|DEFER|R31 R36 R38|pyproject.toml:16|Investigar apenas se simples baseline deixa erro economicamente relevante|Dados suficientes, simulador válido, orçamento finito e avaliação não adaptada|Sofisticação e tuning aumentam seleção; não há ganho incremental comprovado
K18|Carry e basis com custos e capital fragmentado|ECONOMIC_STRATEGY|EXPERIMENTAL|C1|VALIDATE|DEFER|R02 R05 R41 R45|scripts/observe_carry_forward.py:1|Segmentação e demanda por alavancagem podem remunerar carry, com risco de saída|Spot/perp/futuro compatíveis, cada perna financiada, funding/basis e custos|Linha já existe; piloto manual v2 depende da janela; não abrir nova variação de BTC sem motivo material
'''
capabilities=[]
for row in CAPS.strip().splitlines():
    ident,name,purpose,state,c,action,status,refs,path,mechanism,data,risk=row.split('|')
    capabilities.append(dict(id=ident,name=name,purpose=purpose,internal_state=state,C=c,action=action,status=status,references=refs.split(),internal_evidence=path,mechanism=mechanism,data_contract=data,risk=risk,evidence_origin='LOCAL/EXTERNAL separated in references',evidence_scope='ENGINEERING' if purpose!='ECONOMIC_STRATEGY' else 'ECONOMIC',result='NOT_EVALUATED',comparison='NOT_DIRECTLY_COMPARABLE for economic returns',data_accessibility='UNKNOWN',data_pit_quality='UNKNOWN',crypto_transferability='UNKNOWN',execution_feasibility='UNKNOWN',edge_decay_risk='UNKNOWN',competitive_prevalence='UNKNOWN',competitive_gap='UNKNOWN',differentiation_potential='UNKNOWN',redundancy_penalty=0,score_confidence='LOW',priority_score=None))

# Governance estimates, not measured benefits. Unknown economic values stay unscored.
estimates={
'K01':([4.5,4.5,3.5,4,4,5,2],[2.5,2,2,2,3,1]),
'K02':([4,4.5,4,5,2.5,5,3],[1,1,1,1,0,0]),
'K03':([4,5,3,4,4,5,2],[2,2,2,2,3,1]),
'K05':([4.5,5,4,4,3.5,5,3],[2.5,3,2,2,1,1]),
'K06':([4,4,3,3,4,4,2],[4,4,3,3,4,2]),
'K07':([4,4.5,3,4,3,5,2],[2,2.5,2,2,2,1]),
'K08':([4,4.5,3.5,4,4,4,2],[3,3,2,2,3,1]),
'K11':([4,4,3,3,3,5,2],[3,3,2,2,2,1]),
}
vw=[.30,.20,.15,.10,.10,.10,.05];cw=[.25,.20,.15,.15,.15,.10]
vn=['scientific_value','validation_value','external_evidence','architectural_fit','incremental_capability','domain_fit','independent_references']
cn=['implementation_complexity','methodological_risk','dependency_risk','maintenance_cost','data_cost','operational_cost']
for cap in capabilities:
    if cap['id'] in estimates:
        v,c=estimates[cap['id']]
        vs=20*sum(a*b for a,b in zip(v,vw));cs=20*sum(a*b for a,b in zip(c,cw))
        cap.update(score_profile='ENABLER',value_score=vs,cost_risk_score=cs,priority_score=.7*vs+.3*(100-cs),estimated_value=dict(zip(vn,v)),estimated_cost=dict(zip(cn,c)))
        lo_v=20*sum(max(0,a-1)*w for a,w in zip(v,vw));hi_v=20*sum(min(5,a+1)*w for a,w in zip(v,vw))
        lo_c=20*sum(max(0,a-1)*w for a,w in zip(c,cw));hi_c=20*sum(min(5,a+1)*w for a,w in zip(c,cw))
        cap['priority_interval']=[.7*lo_v+.3*(100-hi_c),.7*hi_v+.3*(100-lo_c)]
        cap['weight_sensitivity']={str(w):w*vs+(1-w)*(100-cs) for w in [.6,.7,.8]}
        cap['score_rationale']='Potencial estimado a partir do mecanismo/estado/risco nesta ficha. 0=nulo ou custo baixo demonstrado; 3=material plausível; 5=alto no escopo. Incerteza ±1 por nota, não intervalo estatístico. Dados econômicos não adquiridos permanecem UNKNOWN e gate independente.'
capabilities[1]['result']='POSITIVE'
capabilities[1]['E']=['E1','E2','E5']
for cap in capabilities:
    cap.setdefault('E',['E1'] if cap['C']!='C0' else ['E0'])

dedup={'R21':'Mesmo grupo de capacidade R22; ancestral não é réplica independente','R23':'Comparador adjacente, calendário acionário requer adaptação','R24':'NOASSERTION e manutenção antiga na fotografia; sem instalar ou presumir recursos comerciais gratuitos','R06':'NOASSERTION: ler licença específica antes de integração; sem pandas instalado','R03':'Caminhos de código tentados retornaram 404; aprofundamento não concluído','R04':'Alternativa de framework, sem necessidade demonstrada de substituir engine','R40':'Calendários úteis somente onde há sessão definida; não impor pregão de ações a cripto 24/7','R17':'ETL amplo; avaliar somente se K15 tiver pergunta testável','R18':'Indexador pesado; exigir necessidade antes de nova infraestrutura'}
for row in rows:
    n=NOTES.get(row['id'])
    row['classification']='referência por capacidade'
    if row['id'] in ['R01','R02','R03','R04']:row['classification']='framework quantitativo adjacente'
    if row['type']=='paper':row['classification']='referência científica'
    if row['id'] in ['R47','R48','R49']:row['classification']='produto/serviço; PUBLIC_EVIDENCE_ONLY'
    row['decision_reason']=dedup.get(row['id'],'Avançar apenas como alternativa da capacidade indicada; adoção não autorizada.')
    row['tests']='não inspecionados' if not n else ('asserções amostradas; não executadas' if n[0]=='C2' else 'não executados; ver escopo da ficha')
    row['releases_and_issues']='Não revisados sistematicamente; pushed_at não comprova qualidade/manutenção saudável'
    row['data_required']=row['capability']+'; contrato por instrumento/tempo, ver matriz de capacidade'
    if n:
        row.update(C=n[0],E=['E1'],inspected=n[1],claim=n[2],implication=n[3],capabilities=n[4].split(),evidence_origin='EXTERNAL',evidence_scope='ENGINEERING',result='NOT_EVALUATED')
        if row['id']=='R52': row.update(E=['E1','E5'],result='POSITIVE',evidence_origin='LOCAL',version='SciPy 1.18.0 instalado')
    row['version_observed']=next((d['ref'] for d in deep if d['id']==row['id']),row.get('version','metadata timestamp; commit not pinned'))
    if row['id'] in ['R47','R50']:row['web_verification']='Official documentation also read through web tool; raw fetch unavailable'
    if row['id']=='R45':row['web_verification']='HTTP 202 not treated as valid document; official Binance connector documentation confirms funding endpoint distinction'

experiments=[
dict(id='F01',capability='K01',question='O contrato impede misturar fechamento de barra, recebimento e identidade monetária?',test='Matriz sintética: BTC/USDT versus BTC/USD, revisão tardia, candle aberto, duplicata, contrato linear/inverso e ativo deslistado. Fixar seis contrastes antes de executar. Reutilizar provider/snapshot por adapters sem alterar runtime.',prerequisites='Mapear instrumento com unidades explícitas; seis fixtures sintéticas novas; não usar snapshot expirado como dado corrente.',metric='6/6 violações recusadas no ponto apropriado; casos válidos preservados; registrar limitações onde contrato não representa a distinção.',decision='Qualquer aceitação inválida abre achado de engenharia; não concluir alpha. Não mudar contratos congelados.',next_gate='G1 técnico; nova implementação só após evidência e autorização de integração.',status='READY_FOR_PROTOCOL_REVIEW',budget='0 rede; 6 casos e controles, uma execução por versão'),
dict(id='F02',capability='K03',question='Outra rota confirma os mesmos índices e blocos do estudo Aave?',test='Reusar protocolo já preparado compare_aave_second_source.py, com mesmos blocos/USDC/chain; conferir bytecode/proxy histórico antes de atribuir fórmula a uma versão.',prerequisites='Quota compartilhada disponível; endpoint archive permitido; protocolo existente íntegro; não repetir sondas idênticas malsucedidas.',metric='Identidade de bloco e índice exata em todas as fronteiras previstas; zero divergência inexplicada. Não trocar período/pool após resultado.',decision='Divergência bloqueia a claim afetada; concordância apenas corrobora engenharia da mesma cadeia. Rendimento continua condicional.',next_gate='G1 já existente; G2 só após procedência/limitações. Não integra nem opera.',status='BLOCKED_DATA',budget='Teto existente: 350 RPC/20MB, uma unidade de ingestão, zero retries; não executado nesta rodada'),
dict(id='F03',capability='K04',question='Ranking residual acrescenta informação à heurística de momentum atual após turnover e beta?',test='Uma baseline vigente e uma alternativa residual pré-especificada. Mesmas datas/ativos elegíveis; contraste secundário separado para universo. Calcular IC por data, exposição BTC/ETH, turnover e PnL com custos fixados.',prerequisites='Universo histórico e delistings; labels disponíveis; custos/hedge admissíveis; protocolo/linhagem novos e checagem de família congelada. Não reutilizar 140 semanas já examinadas como holdout.',metric='Incremento líquido versus baseline e IC com blocos temporais; intervalo e tamanho do efeito. Limiar numérico econômico deve ser congelado após admissibilidade, antes de abrir resultados.',decision='Sem poder suficiente => INCONCLUSIVE; custo elimina incremento => rejeitar apenas o contraste. Nenhum tuning adicional nesta tentativa.',next_gate='G1 pendente; no máximo uma principal e uma alternativa econômica ativas.',status='BLOCKED_DATA',budget='2 variantes; sem sweep; horizonte e período ainda pendentes de dados admissíveis'),
dict(id='F04',capability='K06',question='O diagnóstico muda quando fills otimistas são substituídos por limites de fila, atraso e falha de perna?',test='Primeiro replay sintético analítico com fill total, parcial e não fill; depois usar L2/trades admissíveis em três modelos fixos conservador/central/otimista, separando impacto não modelado.',prerequisites='Sequência íntegra de book/trades e relógios. Livros esparsos existentes não identificam fila; não fabricar essa trajetória.',metric='Reconciliação exata de quantidade/caixa sintéticos; intervalo de shortfall/PnL, fração não identificável e capital bloqueado por perna.',decision='Se sinal depende só de fill otimista, adiar mercado; isso não rejeita universalmente mecanismo. Proibir equivalência de stablecoins pelo nome.',next_gate='G1 sintético; replay histórico condicionado ao contrato e licença.',status='BLOCKED_DATA',budget='3 modelos fixos, sem ajuste aos lucros; aquisição ainda não autorizada como recorrência'),
dict(id='F05',capability='K05',question='As fronteiras de treino e avaliação removem todos os labels que atravessam o corte?',test='Fixtures com término variável de labels; comparar purging por intervalos contra TimeSeriesSplit/gap e referência skfolio. Controle vazado deve falhar. SPA/PBO só em perdas comparáveis após esse teste.',prerequisites='Manifesto de início/fim dos labels e orçamento de tentativas; ambiente isolado para qualquer dependência nova.',metric='Zero interseções entre informação/labels proibidos e treino; 100% dos vazamentos plantados detectados; contabilizar amostra remanescente.',decision='Gap insuficiente indica inadequação do desenho; não mudar o resultado de trial antiga. Ausência de vazamento nos casos sintéticos não certifica pipeline inteiro.',next_gate='G1 técnico; G2 econômico requer poder e amostra próprios.',status='READY_FOR_PROTOCOL_REVIEW',budget='6 fixtures, 2 controles; 0 rede na fase inicial'),
]

registry={'run_id':'20260911T0233','mode':'RESEARCH_AND_BENCHMARK','created_at':dt.datetime.now(dt.UTC).isoformat(),'baseline_sha':SHA,'candidates':rows,'capabilities':capabilities,'next_experiments':experiments,'deep_sources':deep,'technical_benchmarks':bench,'coverage_limit':'53 candidatos triados; 15 fichas de alegações com código/execução amostrados. Não é auditoria integral de 15 repositórios, nem levantamento completo de issues/releases/licenças. Economia não reexecutada.'}
(DOC/'REGISTRY.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf-8')

base_text=f'''# Baseline factual — 20260911T0233

Fotografia local observada em {baseline['observed_at']}. Checkout `C:\\Cripto\\pesquisa-20260909`, branch `{baseline['branch']}`, HEAD `{SHA}`. `git ls-remote` confirmou o mesmo SHA em main. A alteração preexistente de `docs/NEXT_CHAT_PROMPT.md` foi preservada; não fizemos reset, stash, commit, push ou merge.

Autoridade desta rodada: pedido atual para executar os dois arquivos fornecidos, no modo RESEARCH_AND_BENCHMARK. Autorizações mais amplas de integração/publicação no mandato antigo não foram herdadas. Regras locais de `C:\\Cripto\\AGENTS.md` lidas; trabalho sem subagentes. Um clone iniciado antes de localizar essa regra foi interrompido e preservado em `C:\\Cripto\\clone-incompleto-open-source-20260911`; não foi usado como baseline.

## Estado científico e proteção

Charter {link('charters/scientific_state.json')}: H1/H2/H3/H5 CLOSED_NO_GO; H4/H6/H9 CLOSED_INSUFFICIENT_SAMPLE; H7/H8 REGISTERED_NOT_ACTIVATED. Nenhuma autorização de capital/alavancagem/trading LLM. H6/H9 insuficientes não são refutações. Manifestos de congelamento antigos têm escopo histórico; as linhas posteriores são separadas.

Carry manual v2: janela de entrada 12/09/2026 00–01 UTC. LLM pareado v3: 12/09 a 04/12 12–13 UTC, último target possível 13/12; executor congelado `595f120` em área própria. Não foram lidos resultados futuros, alterados protocolos, atualizados hashes desses executores ou acionadas coletas. Não executamos avaliadores econômicos/harness oficiais, treinamento, sweep, observadores ou serializados externos.

## Ambiente efetivamente identificado

{table(['Componente','Versão instalada'],baseline['versions'].items())}

Python {baseline['python']}; {baseline['platform']}. Dependências declaradas em pyproject são faixas, com resolução em uv.lock; pacote declara licença Proprietary. pandas não instalado. Nenhuma instalação foi feita. Core/Ops estão instalados; shims internos não são novas implementações independentes.

## Fluxos confrontados

1. Discovery CoinGecko escolhe candidatos com momentum/trending, volume e exclusão de stable/wrapped/staked ({link('GarimpoInvestimentos/collectors/discovery.py',18)}). Isso atende uma triagem direcional; usar essa exclusão como universo de toda pesquisa impediria investigar staking e rendimento.
2. Fase1 ingere DPL e serve snapshot para features, prefiltro, notícias/LLM e persistência ({link('GarimpoInvestimentos/phase1.py',207)}). CCXT provider faz validação OHLCV e descarta barra aberta. Manifesto fixa sete símbolos Binance e seis Kraken; CoinGecko amplia discovery, mas não prova cobertura histórica admissível.
3. Features diárias v4 exigem intervalo diário, duplicatas ausentes e sufixo contíguo. Volume base × close é aproximação da moeda de cotação, com flag, não volume exato nem conversão USDT/USD ({link('GarimpoInvestimentos/dpl/feature_engineering.py',66)}).
4. Feature Store persiste snapshots e inputs com hash; raw_market_data usa upsert. Snapshot não é recibo HTTP integral, e sua existência não torna toda a base imutável ({link('GarimpoInvestimentos/dpl/feature_store.py',182)}; {link('GarimpoInvestimentos/dpl/snapshots.py',43)}).
5. Backtest usa Spearman/IC e helpers Core; V3 separa HMM, features, WFA e custos. Funding realizado está separado do cenário de funding constante do CostModel. V3 retorna UNVALIDATED; família HMM congelada não ganha permissão por testes sintéticos ({link('GarimpoInvestimentos/v3/backtest_v3.py',1072)}).
6. Pesquisa de carry/basis, altcoins e Aave vive também em scripts e dados externos ao Git. Planejador v3 verifica clocks/identidade, e o coletor Aave verifica reserva, bloco/sucessor e índice. Isto confirma capacidade de pesquisa parcial, não execução em conta.

## Dados observados em modo somente leitura

SQLite aberto com mode=ro e PRAGMA query_only: 200 barras, 3 previsões, 2 market_snapshots e 1 prediction_inputs. Apenas contagens, schema e campos de identificação dos snapshots foram examinados; textos LLM, credenciais e transcrições privadas não foram expostos.

Snapshot atual v4: available_at=2026-09-10 00:00 UTC, collected_at=02:12:15 UTC. A regra de 26h expira em **11/09 02:00 UTC**, anterior à inspeção. O v3 antigo também não atende o contrato atual. Isso exige dados frescos para novo diagnóstico operacional, mas não bloqueia pesquisa offline. Nenhuma ingestão de renovação foi executada.

Quotas: schema do banco examinado somente leitura; contadores não resetados. Limites documentados 28 ingestões, 8 notícias/provedor, 6 LLMs/provedor por dia UTC não são teto monetário universal. Não consumimos APIs financeiras nesta rodada. Requests de documentação e GitHub têm recibos separados.

## Cobertura e checks

Inventário com hashes de {len(baseline['inventory'])} arquivos Python em baseline.json. Inventário não equivale a leitura. Foram lidos pontos de entrada/protocolos e trechos de implementação DPL, snapshots, features, discovery/prefiltro, custos, PBO, Spearman, macro, HMM, execução e Aave. Core foi rastreado via shims/versões; não houve auditoria integral do pacote.

33 testes sintéticos locais passaram na execução corrigida do runner. Primeira tentativa: 27 passaram e 6 falharam porque o bloqueio de socket também bloqueava o loopback do asyncio Windows. Ambos os XML/recibos foram preservados; correção somente no runner novo. Benchmark B01/B02 aprovado, ver EXPERIMENTS.

CI YAML atual lido (quality, all-extras, container, python-314-experimental). Checks remotos do SHA **não reconfirmados nesta rodada**: API pública atingiu limite durante descoberta; contagens anteriores do README são históricas. Não executamos suíte completa, build, Docker ou tipagem; não há mudança operacional a integrar. Esta baseline é factual com cobertura explícita, não certificação integral.

SHA-256 de charter, trials, lock e documento modificado preexistente ficam em baseline.json; conferência final em preservation_final.json. Bases históricas, backups e diários foram localizados pelos índices, sem restauração ou rehash integral. A documentação anterior sobre Aave/carry é evidência histórica, não resultado refeito aqui.
'''
(DOC/'BASELINE.md').write_text(base_text,encoding='utf-8')

survey='''# Survey — descoberta e comparação externa

Registro único: REGISTRY.json; notas e tabelas abaixo são derivadas. As 53 entradas representam candidatos, não 53 recomendações. Foram consultados 40 metadados de repositórios e 13 referências de papers/documentação/fontes. Quinze fichas focadas têm código inspecionado ou benchmark; o aprofundamento Nautilus ficou pendente após 404 nos dois caminhos tentados. Não se preencheu essa lacuna inventando evidência.

Onda 1: baseline local e sementes de engines/feeds/validação. Onda 2: contratos DeFi, on-chain, opções, fatores, macro e artigos de mecanismos. Onda 3: restrições, falsos positivos/negativos e independência. Teto escolhido para esta rodada: 53 candidatos e 15 fichas focadas, sem novas instalações. O limite público GitHub foi encontrado após os 40 metadados; não houve retries para contorná-lo. Encerramento por orçamento de cobertura, não alegação de saturação do ecossistema.

HTTP 200 comprova obtenção do documento, não correção da alegação. HTTP 202 da página Binance não foi aceito como conteúdo validado. FRED/Glassnode foram lidos pela ferramenta web após falha no download documental; unlocks permaneceu inacessível por limite de tamanho. Não usamos agregadores, Reddit ou publicidade como certificação.

Licença abaixo é detecção da API GitHub, não análise jurídica ou autorização de redistribuição. NOASSERTION/UNKNOWN não significam domínio público. Aave MathUtils tem SPDX BUSL-1.1; sua aplicabilidade exige a licença completa e versão. Não copiamos código externo para produção. `pushed_at` registra atividade observada, sem provar qualidade; issues, releases, CVEs e licenças de dados/modelos permanecem pendentes de revisão sistemática.

'''
survey+=table(['ID','Candidato / fonte primária','Tipo/capacidade','Licença observada','C','Decisão de triagem'],[(r['id'],f"[{r.get('repository',r.get('name'))}]({r['url']})",r['type']+' / '+r['capability'],r.get('license','UNKNOWN'),r['C'],r['decision_reason']) for r in rows])
survey+='\n## Quinze fichas de capacidade\n\nAs referências a linhas descrevem trechos efetivamente lidos; baixar outros arquivos não os promove a C1/C2. Nenhum framework externo foi executado integralmente.\n\n'
for r in rows:
    if r['id'] not in NOTES:continue
    n=NOTES[r['id']]
    survey+=f"### {r['id']} — {r.get('repository',r.get('name'))}\n\nReferência: [{r['version_observed']}]({r['url']}); nível {n[0]}. Inspeção: `{n[1]}`.\n\n**CODE_VERIFIED:** {n[2]}\n\n**INFERENCE / decisão:** {n[3]} Capacidades: {n[4]}. E1 de implementação; somente R52 tem E5 local aqui. Nenhuma eficácia econômica transferida.\n\n"
survey+='''## Mecanismos e evidência científica

- R41, [BIS Crypto carry](https://www.bis.org/publications/working-paper-1087-crypto-carry): sumário consultado; trata basis de BTC/ETH e sua relação com condições de mercado. Motiva segmentação e demanda de alavancagem; não transfere rentabilidade ao capital/fees/venues deste PC. Não reproduzimos o paper nem certificamos E3/E4 integral.
- R42, [Liu, Tsyvinski e Wu](https://www.nber.org/papers/w25882): referência de fatores cripto para organizar ranking e exposições. Papel de mercado/tamanho/momentum é candidato de explicação; observações históricas e universo do estudo não são holdout nosso. Página/abstract consultados, artigo completo não replicado.
- R43, [Cawley e Talbot](https://jmlr.org/papers/v11/cawley10a.html): seleção pode sobreajustar o próprio critério de avaliação. Implicação: incluir seleção de filtros/modelos no desenho, não apenas treinar parâmetros dentro de folds. Não mede o tamanho desse viés no projeto.
- R44, [Loss-versus-rebalancing](https://arxiv.org/abs/2208.06046): perda relativa ao rebalanceamento é lente para separar taxas de seleção adversa em AMMs. Não equiparar benchmark idealizado a execução real ou conclusão universal de prejuízo de LP.

Essas quatro entradas foram triagem metodológica por páginas/resumos, não análise integral de métodos/apêndices/dados. Novas redes/RL, staking e eventos foram cobertos na triagem e no mapa de dados; não houve deep dive em toda família. Isso permanece uma limitação material da amplitude científica solicitada.

## Independência e resultados negativos

Alphalens-reloaded deriva de Alphalens e importa SciPy; duas entradas não são duas replicações de rank IC. CCXT dentro do projeto e no framework externo compartilha dependência. Aave/DefiLlama podem ler a mesma cadeia: concordância verifica extração, não gera nova amostra de mercado. Autor desta rodada é o mesmo agente em todas as verificações, sem revisão humana/externa independente.

[Freqtrade](https://docs.freqtrade.io/en/latest/lookahead-analysis/) documenta sinais não acionados como fonte de falso negativo e dependência de pairlist como falso positivo. [hftbacktest](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) assume ausência de impacto próprio no replay. Hummingbot testa equivalência entre quotes estáveis; essa regra não deve substituir identidade/câmbio no estudo. Aave core está arquivado na fotografia; localizar versão implantada por bloco continua necessário. Nenhuma dessas limitações refuta todos os usos das ferramentas.
'''
(DOC/'SURVEY.md').write_text(survey,encoding='utf-8')

matrix='# Matriz de capacidades e contratos\n\nClassificação por capacidade e alegação. DESCONHECIDO significa inspeção insuficiente, não ausência provada.\n\n'
matrix+=table(['ID','Capacidade','Estado interno / C','Ação / estado','Referências','Evidência interna'],[(c['id'],c['name'],c['internal_state']+' / '+c['C'],c['action']+' / '+c['status'],', '.join(c['references']),c['internal_evidence']) for c in capabilities])
matrix+='\n## Contrato, valor incremental e limitações\n\n'
for c in capabilities:
    p,l=c['internal_evidence'].rsplit(':',1)
    matrix+=f"### {c['id']} — {c['name']}\n\nFinalidade: {c['purpose']}. {link(p,l)}.\n\nMecanismo: {c['mechanism']}.\n\nDados/PIT: {c['data_contract']}. Limite: {c['risk']}. DATA_ACCESSIBILITY/DATA_PIT_QUALITY de novos datasets = UNKNOWN até verificação. Pesquisa documental é admissível; experimento econômico e integração têm gates separados. Comparação econômica com produtos externos: NOT_DIRECTLY_COMPARABLE.\n\n"
matrix+='''## Prioridade: potencial e custo separados

Perfil ENABLER usa pesos 0,30 ciência + 0,20 validação + 0,15 evidência externa + 0,10 arquitetura + 0,10 incremento + 0,10 domínio + 0,05 referências independentes. Custo usa 0,25 complexidade + 0,20 risco metodológico + 0,15 dependências + 0,15 manutenção + 0,15 dados + 0,10 operação. VALUE e COST =20×nota; PRIORITY=0,70×VALUE+0,30×(100−COST). Notas e sensibilidade estão no JSON.

As notas são estimativas de governança, de baixa confiança. Intervalo abaixo propaga ±1 em cada nota, limitado a 0–5; não é IC estatístico. Não transformar pequenas diferenças em prioridade robusta. Prioridade não remove BLOCKED_DATA. Benefício econômico, acessibilidade/PIT e viabilidade de execução desconhecidos permanecem UNKNOWN, sem nota zero; estratégias não recebem score preciso.

'''
ranked=sorted([c for c in capabilities if c['priority_score'] is not None],key=lambda c:-c['priority_score'])
matrix+=table(['ID','Valor','Custo/risco','Prioridade estimada','Intervalo ±1','Confiança / gate'],[(c['id'],f"{c['value_score']:.1f}",f"{c['cost_risk_score']:.1f}",f"{c['priority_score']:.1f}",f"{c['priority_interval'][0]:.1f}–{c['priority_interval'][1]:.1f}",'LOW / '+c['status']) for c in ranked])
matrix+='\nOs intervalos se sobrepõem: priorizar por dependências e valor da decisão. K02 é barato e parcialmente concluído; K01/K03/K05 habilitam avaliações; K06 tem alto custo e dados insuficientes. Não existe ranking econômico numérico defensável nesta rodada. Prevalência/gap/diferenciação = UNKNOWN: não foram contados comparadores representativos. Não aplicamos desconto de redundância depois de agrupar forks/alternativas. NO_VERIFIED_ADVANTAGE econômico. Há controles internos úteis verificados, sem superioridade universal.\n'
matrix+='\n## Vistas por categoria (IDs do mesmo backlog)\n\n'+table(['Categoria','Prioridades condicionais'],[
('Melhorias imediatas','K02 → K01 → K07'),('Novas análises','K04 → K10 → K14'),('Filtros/ranking','K01 → K04; separar elegibilidade, validade, seleção e risco'),('Fontes/datasets','K03 → K08 → K15; documentos não equivalem a dados adquiridos'),('Ferramentas','R52 / R27 já instaladas; R22 / R25 / R07 candidatos isolados'),('Features/estratégias','K04 / K12 / K18 antes de K17, condicionados a dados; não prova de maior alpha'),('Validação','K02 → K05 → K03'),('Risco/execução','K07 → K11 → K06'),('Referências','R05 / R52 / R10 / R22 / R25, conforme capacidade'),('Composições','K01+K04+K11; K03+K12+K11; K01+K06+K07')])
(DOC/'CAPABILITY_MATRIX.md').write_text(matrix,encoding='utf-8')

exp=f'''# Experimentos e recibos

## Executado nesta rodada

G1 de B01/B02 foi gravado antes da execução em BENCHMARK_PROTOCOL.json. Baseline e comparação inicial já estavam identificadas. Dados sintéticos, seed 20260911, tolerância absoluta 1e-10, orçamento finito e nenhuma variante econômica. Script próprio com rede bloqueada, configuração sintética e diretórios isolados; referências numéricas já instaladas. Não foi executado código baixado dos frameworks.

{table(['Estudo','Resultado','Evidência e limite'],[
('B01 Spearman/ranks',f"100 casos; 0 divergências; erro máximo {bench['B01']['max_error']:.3g}; constante indefinida",'C4 / E5 LOCAL ENGINEERING POSITIVE; não avalia p-value, IC, bootstrap ou alpha'),
('B02 SMA/Bollinger',f"231 prefixos; erro máximo {bench['B02']['max_reference_error']:.3g}; vazamento plantado detectado em 230 prefixos",'C4 / E5 LOCAL ENGINEERING POSITIVE; SMA/Bollinger apenas, sem provar causalidade do pipeline inteiro'),
('Testes locais selecionados','33 passaram; zero falhas na execução v2','DPL/router fake, PBO sintético, custos e contabilidade; C3 somente asserções exercitadas'),
('Primeiro runner','27 passed / 6 failed','Erro de infraestrutura: bloqueou socketpair local do asyncio Windows; primeira tentativa preservada')])}

Tempo do núcleo B01/B02: {bench['elapsed_seconds']:.3f}s, exclui import/startup. Não é comparação de throughput entre engines e não mede memória. Inicialização completa demorou mais; não atribuir os 0,37s ao comando inteiro. Nova execução v2 dos testes permitiu somente loopback para infraestrutura Windows, mantendo conexão externa recusada.

Comandos efetivamente usados:

```powershell
C:\\Cripto\\CRIPTO.cmd python C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233\\work\\benchmark.py
C:\\Cripto\\CRIPTO.cmd python C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233\\work\\verify_selected.py
C:\\Cripto\\CRIPTO.cmd python C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233\\work\\verify_selected_v2.py
```

Recibos imutáveis por hash no manifesto da entrega. Reproduzir em diretório novo para não sobrescrever esta rodada. Não executar scripts de registro canônico/harness para reproduzir estes testes.

## Até cinco próximos experimentos

As propostas abaixo não criam cinco hipóteses econômicas ativas. Só F03 busca incremento econômico novo; F02 verifica a linha existente. Gates pendentes e decisões quantitativas ainda não congeladas estão explícitos.

'''
for e in experiments:
    exp+=f"### {e['id']} / {e['capability']} — {e['question']}\n\nTeste mínimo: {e['test']}\n\nPré-requisitos: {e['prerequisites']}\n\nMétrica/critério: {e['metric']}\n\nDecisão: {e['decision']} Próximo gate: {e['next_gate']} Estado: {e['status']}. Orçamento: {e['budget']}.\n\n"
exp+='''## Composições e ablações

- Universo histórico + ranking residual + hedge/risco: manter sinal constante na análise de cobertura e universo constante no contraste do algoritmo; reportar separadamente interseção e cobertura nova. F03 não permite alterar tudo e atribuir ganho ao ranking.
- Índice Aave + caixa de saída + stress de depeg/custos: decompor juros, reserva consumida, conversão e perdas de cauda. Segunda RPC confirma dados; não confirma taxas pessoais nem cria E6.
- Order flow + regime causal + replay: medir ganho incremental sobre spread/depth simples; ablação de regime separada, sem reabrir HMM congelado. Só após dataset admissível.

Economia nesta rodada: NOT_EVALUATED. Não houve nova coleta de mercado, backtest econômico, observação prospectiva ou resultado financeiro. Nenhum E6-H/E6-P foi concedido. Protocolos carry/LLM existentes aguardam janelas e invocação manual; não há tarefa em segundo plano.
'''
(DOC/'EXPERIMENTS.md').write_text(exp,encoding='utf-8')

dec='''# Decisões da rodada

1. **KEEP / VALIDATE DPL, snapshots, métricas e custos existentes.** Testes e benchmarks selecionados sustentam propriedades concretas. Não há motivo demonstrado para reescrever esses componentes só para adotar framework.
2. **IMPROVE a distinção de universos por mecanismo.** Exclusão de stable/wrapped/staked é compreensível na triagem direcional, mas não deve reger lending, staking, LP ou arbitragem. Abrir linha separada exige contrato e dados, não remover filtros silenciosamente.
3. **AUGMENT validação e ranking antes de sofisticar modelos.** K01/K02/K05 são habilitadores; K04 é pergunta econômica testável. Bibliotecas são alternativas, não backlog de instalações.
4. **VALIDATE Aave pela mesma identidade histórica e segunda fonte.** R10 arquivado e R09 APY snapshot não são oráculos para todo contrato implantado. O estudo existente já usa índices; repetir APY não é progresso.
5. **DEFER filas de HFT, RL e opções como integração.** Há capacidades interessantes, mas dados/infraestrutura/contratos insuficientes. Isso não refuta os mecanismos.
6. **REJECT o reuso automático de equivalência entre stablecoins, funding uniforme, preço last como fill ou APY como retorno realizado.** Escopo rejeitado são essas premissas para o nosso uso, não os projetos inteiros.
7. **Não reabrir H1–H6/H9 nem trocar executores manuais.** H4/H6/H9 continuam insuficientes; H7/H8 não ativadas. G1 técnico não libera capital e a evidência dos mesmos dados não é nova amostra.
8. **Preservar o diagnóstico de snapshot expirado.** Renovação é ação operacional fora da necessidade desta rodada; não consumimos quota para tornar o relatório mais favorável.

## O que não foi concluído

Issues/releases e licenças completas por referência; deep dive Nautilus; artigos integrais e replicações negativas externas; CI atual pela API; auditoria de todos os módulos e dados preservados; ranking econômico quantitativo; aquisições PIT/segunda RPC e estudo completo das composições. Não declarar a auditoria ampla integralmente concluída. A rodada entrega decisões utilizáveis e cobertura verificável, com continuação delimitada em EXPERIMENTS.

Não houve alterações no código operacional, bibliotecas, locks, charters, trials, modelos, bancos operacionais, quotas ou agendamentos; somente artefatos de pesquisa, scripts isolados e diretórios temporários de teste. Documento preexistente modificado pelo usuário foi preservado. Nenhum commit, PR, push, merge, ordem ou pagamento.
'''
(DOC/'DECISIONS.md').write_text(dec,encoding='utf-8')

report=f'''# Cripto Predictor — resultado da rodada de pesquisa

**A decisão desta rodada é preservar o núcleo existente e ampliar validação, contratos temporais, ranking e execução simulada por estudos separados.** Não apareceu evidência que justifique trocar o sistema por um bot externo ou promover qualquer estratégia a capital.

Execução no commit `{SHA}`, com alteração documental preexistente preservada. O pedido foi aplicado ao Cripto; o segundo arquivo era o guia de uso, não uma solicitação de executar também o Stocks.

## Entrega comprovada

- **53 candidatos triados**, com 40 metadados de repositórios e 13 fontes/artigos/documentações; **15 fichas focadas** com implementação examinada ou benchmark. Não confundir com 15 auditorias integrais.
- **18 capacidades**, agrupadas por problema e com estados, referências, contratos, ações e gates em REGISTRY.json.
- **Dois benchmarks sintéticos aprovados**: 100 casos de Spearman; 231 prefixos de SMA/Bollinger. **33 testes selecionados aprovados**. A primeira falha de isolamento Windows foi preservada e resolvida no runner da auditoria.
- Leitura readonly do banco confirmou **200 barras, 3 previsões, 2 snapshots e 1 input**. Snapshot v4 expirou em **11/09/2026 02:00 UTC**; isso não foi ocultado nem corrigido com coleta fora desta rodada.
- Sem implantação, dependências novas, operação financeira ou alterações nos protocolos congelados.

## Achados que mudam decisões

**Já há mais que forecasting.** Código e registros incluem DPL, controle de custos, carry/basis, altcoins e Aave. A limitação não é simplesmente ausência de frameworks; são contratos de dados, poder/amostra e condições de execução para cada pergunta. Discovery direcional exclui stablecoins e staking: essa escolha não deve limitar pesquisas de rendimento e risco.

**Referências externas também impõem premissas.** Hummingbot aceita pares estáveis como intercambiáveis no executor examinado; hftbacktest não incorpora impacto da própria ordem; Alphalens-reloaded usa SciPy e deriva de Alphalens. Logo, integração não traz automaticamente identidade monetária, fills realistas ou independência científica.

**Aave exige comparação do objeto correto.** O adapter DefiLlama examinado apresenta taxa anualizada instantânea em apyBase; o estudo local reconstrói renda por índices. Não substituir índices realizados por APY exibido. A referência aave-v3-core arquivada ajuda a entender a fórmula, mas exige vincular versão implantada ao bloco; segunda rota RPC continua pendente.

**Resultados técnicos favoráveis são limitados.** Spearman/SMA/Bollinger concordaram com as referências dentro da tolerância, sem evidência de erro nesses casos. Isso sustenta KEEP/VALIDATE nesse escopo; não certifica todos os indicadores, causalidade do pipeline, eficácia de filtros ou rentabilidade.

## Respostas às perguntas do mandato

{table(['Pergunta','Conclusão no escopo observado'],[
('1. O que faz e o que está protegido?','Pesquisa por DPL/LLM/V3 e scripts econômicos; H1–H6/H9 encerradas conforme charter, H7/H8 não ativadas; executores futuros preservados.'),
('2. Informações e filtros faltantes/mal utilizados?','PIT de universo e entidades, FX/settlement explícitos, eventos de funding por contrato, vintages macro e trajetória de fila são prioridades. Não afirmar ausência global sem inventário completo.'),
('3. Limitação a poucas moedas/famílias?','Fachada CCXT tem mapas limitados e discovery direcional; pesquisa externa/local já cobre outros mecanismos. Universo deve ser definido por pergunta, sem excluir fracassos retrospectivos.'),
('4. Spot, derivativos, relativo, eventos, on-chain, DeFi?','Mapeados em K04/K07–K18; maior profundidade em contratos, validação, Aave e execução. Eventos/entidades/RL ficaram em triagem.'),
('5. O que perde interesse após custos?','Histórico local documenta perdas de carry sob stress e famílias HMM sem promoção; não refeito aqui. LP/market making exigem seleção adversa; fees/APY/basis brutos não bastam.'),
('6. Fontes e implementações úteis?','CCXT já existente, SciPy/NumPy como referência; Alphalens para ranking, arch/skfolio para validação, cryptofeed/hftbacktest para microestrutura, contratos/RPC para Aave.'),
('7. Transferibilidade atual?','Verificada parcialmente por implementação e documentação; retornos externos NOT_DIRECTLY_COMPARABLE. Sem replicação econômica externa ou E6 transferido.'),
('8. Vantagens/commodity/componentes novos?','Controles internos úteis verificados; NO_VERIFIED_ADVANTAGE econômico. Reutilizar interfaces estreitas antes de engine novo. Não estimamos percentual substituível.'),
('9. Maior ganho incremental?','Diferenciais e PIT, seguidos de seleção/risco testáveis. Composições universo+ranking+hedge e índice+liquidez+stress precisam ablações.'),
('10. Até cinco próximos experimentos?','F01 contrato/relógios; F02 Aave segunda rota; F03 ranking residual; F04 fills/duas pernas; F05 fronteiras e multiplicidade. Nenhum requer operar capital.')])}

## Prioridade prática

Concluir especificações sintéticas F01/F05 e o contrato de dados de F03. F02 reutiliza a preparação já existente, condicionada a quota/acesso; F04 aguarda trajetória L2/trades adequada. Não ativar cinco linhas econômicas: preservar no máximo uma principal e uma alternativa conforme regras locais.

Não há lucro novo medido nesta rodada. Os resultados históricos de Aave/carry mantêm suas datas e limitações; insuficiência de dados não foi tratada como refutação. Nenhum resultado prospectivo foi produzido antecipadamente.

## Navegação e limites de conclusão

- [Baseline factual](BASELINE.md): commit, ambiente, fluxos, dados e cobertura.
- [Survey e quinze fichas](SURVEY.md): candidatos, evidências externas e limites.
- [Matriz e prioridades](CAPABILITY_MATRIX.md): 18 capacidades, scores estimados e sensibilidade.
- [Experimentos](EXPERIMENTS.md): resultados executados, recibos e cinco propostas.
- [Decisões](DECISIONS.md): manter/adicionar/adiar/rejeitar e pendências.
- [Registro estruturado](REGISTRY.json): fonte das tabelas e rastreabilidade.

**A auditoria ampla solicitada ainda tem partes materiais pendentes:** aprofundamento sistemático de issues/releases/licenças, artigos integrais, módulos/dados não examinados, CI atual e validações econômicas. Esta entrega é uma rodada inicial executada e delimitada, não declaração de trabalho integral concluído. Evidências completas locais ficam em `C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233`; documentação da iniciativa em `docs/open_source_research/20260911T0233`.
'''
(DOC/'REPORT.md').write_text(report,encoding='utf-8')

for name in ['baseline.json','benchmark_result.json','BENCHMARK_PROTOCOL.json','selected_tests.xml','selected_tests_receipt.json','selected_tests_v2.xml','selected_tests_v2_receipt.json']:
    shutil.copy2(ROOT/name,DOC/name)
shutil.copytree(ROOT/'work',DOC/'reproduction',dirs_exist_ok=True,ignore=shutil.ignore_patterns('isolated','__pycache__'))
print(json.dumps({'documents':str(DOC),'candidates':len(rows),'focused_reviews':len(NOTES),'capabilities':len(capabilities),'next_experiments':len(experiments)},ensure_ascii=False))
