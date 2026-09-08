import hashlib
import json
import math
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

work = Path(__file__).parent
data = work/'carry-data'
root = work/'cripto-v1.2'
out = work.parent/'outputs'
evidence = root/'docs/evidence/funding_carry_screen_20260907'
r=json.loads((data/'results.json').read_text())
sources=json.loads((data/'manifest.json').read_text())
for entry in sources:
    assert hashlib.sha256((data/entry['artifact']).read_bytes()).hexdigest()==entry['sha256']
for symbol,asset in r['assets'].items():
    rows=json.loads((data/(symbol+'_funding.json')).read_text())
    decimal_sum=sum(Decimal(row['fundingRate']) for row in rows)
    primary=next(w for w in asset['windows'] if w['days']==365)
    assert abs(float(decimal_sum)-primary['rate_sum'])<1e-14
    assert primary['n']==1095
    assert asset['fixed_quantity']['eligible_settlements']==1094
    assert asset['normalized_notional']['funding_brl_5000_zero_cost']<r['benchmark']['net_gain_brl_range'][0]

public_sources=[
    {'name':'Funding history endpoint and pagination','url':'https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History','observed':'Public settlement data; no fills or strategy validity.'},
    {'name':'Binance public spot fees','url':'https://www.binance.com/en/fee/trading','observed':'Regular User: maker/taker 0.100% per side; account-specific eligibility unverified.'},
    {'name':'Binance public futures example','url':'https://www.binance.com/en/support/faq/detail/360033544231','observed':'2bps maker/5bps taker example explicitly hypothetical; current account tariff UNKNOWN.'},
    {'name':'PTAX latest close','url':'https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do','observed':'2026-09-04: bid5.1247 ask5.1253 BRL/USD; accounting mark, not executable FX quote.'},
    {'name':'Tesouro Reserva','url':'https://www.tesourodireto.com.br/tesouro-reserva','observed':'100% Selic, B3 custody0.20% above R$10000, initially BB; operator access unknown.'},
    {'name':'B3 treasury taxation','url':'https://www.b3.com.br/pt_br/produtos-e-servicos/tesouro-direto/tesouro-direto/perguntas-frequentes/','observed':'17.5% IR at361-720days, custody0.20% with R$10000 exemption; conditional PF illustration.'},
    {'name':'Federal Receita offshore FAQ','url':'https://www.gov.br/fazenda/pt-br/acesso-a-informacao/perguntas-frequentes/tributacao-offshore/perguntas-e-respostas-offshores-in-rfb-2-180-22-05-24.pdf','observed':'Virtual-asset classification and location affect treatment. 15% is only a sensitivity in this report, not a determination of operator tax liability.'},
    {'name':'Funding mechanism','url':'https://www.binance.com/en/academy/articles/what-are-funding-rates-in-crypto-markets','observed':'Rate applies to position value at settlement; payment sign can reverse.'},
]
for s in public_sources:s['access_date']='2026-09-07'
manifest={'as_of':'2026-09-07','raw_requests':sources,'documentary_sources':public_sources,
          'protocol_commit':'d85d75b','known_at_policy':'download timestamps, never retroactive availability',
          'quality':'2190 unique funding records, complete365days; final daily candle uses only the opening quote at cutoff; its later OHLC fields excluded',
          'checks':['raw SHA256 verified','Decimal independently matches float aggregate','two assets and three windows retained','spot+short price P&L equals endpoint basis difference'],
          'no_runtime_changes':True,'no_capital_or_collection_changes':True}
(evidence/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
shutil.copyfile(data/'results.json',evidence/'results.json')

def money(x):
    return f'{x:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def pct(x):return f'{100*x:.2f}%'.replace('.',',')
btc,eth=r['assets']['BTCUSDT'],r['assets']['ETHUSDT']
window_table='\n'.join(f"| {days} dias | {pct(next(w for w in btc['windows'] if w['days']==days)['simple_annualized_rate'])} | {pct(next(w for w in eth['windows'] if w['days']==days)['simple_annualized_rate'])} |" for days in [30,90,365])
cash_table='\n'.join(f"| {symbol[:3]} | US$ {money(a['fixed_quantity']['funding_usdt'])} | US$ {money(a['fixed_quantity']['basis_change_usdt'])} | US$ {money(a['fixed_quantity']['fee_illustration_usdt']+a['fixed_quantity']['slippage_5bps_each_side_usdt'])} | **R$ {money(a['fixed_quantity']['net_scenario_brl_fx_unchanged'])}** |" for symbol,a in r['assets'].items())
fx_table='\n'.join(f"| {int(100*b['usdbrl_change']):+d}% | R$ {money(b['gross_of_tax_value_brl'])} | R$ {money(e['gross_of_tax_value_brl'])} |" for b,e in zip(btc['fx_sensitivity'],eth['fx_sensitivity']) if b['usdbrl_change'] in [-.1,0,.1])
report=f'''# Funding carry: decisão econômica — 07/09/2026

**Decisão: não aprofundar agora o carry passivo de BTC/ETH nesta estrutura de
US$5.000 e com o benchmark em BRL adotado como referência.** A remuneração
observada ficou muito abaixo do custo de oportunidade, inclusive em cenários
que favorecem o carry. Isso encerra esta triagem; não prova que toda forma de
carry, venue, ativo ou período futuro seja incapaz de gerar lucro.

## A conta que importa

Estrutura ilustrativa sem empréstimo: US$2.500 de spot + US$2.500 de margem
USDT separada; quantidade igual vendida no perpétuo. Spot e futuro cancelam
a maior parte da exposição à direção da criptomoeda. Os ganhos restantes são
funding e mudança do diferencial entre os preços das duas posições.

Conta histórica de 07/09/2025 a 07/09/2026, com quantidade fixa, preços de
referência e câmbio constante de R$5,1253 por USD. Não são operações realizadas:
fees e slippage abaixo são cenários, e mark price não é preço de execução.

| Ativo | Funding recebido | Mudança de basis | Fees + slippage ilustrativos | Saldo em BRL |
|---|---:|---:|---:|---:|
{cash_table}

Os saldos são **antes de imposto, custos cambiais, atenção e prêmio de risco**.
O funding da entrada foi excluído: comprar após a liquidação não dá direito
a receber aquela parcela. Foram utilizados 1.094 pagamentos subsequentes.

A alternativa candidata, Tesouro Reserva, gera aproximadamente **R$2.900 a
R$2.907 em 365 dias** no cenário de Selic efetiva constante de 13,90%, IR17,5%,
custódia B3 e isenção disponível de R$10mil. Acesso do operador ao produto,
taxas adicionais e tributação pessoal continuam não confirmados. Não é taxa
líquida contratada nem promessa. [Tesouro Reserva](https://www.tesourodireto.com.br/tesouro-reserva),
[B3](https://www.b3.com.br/pt_br/produtos-e-servicos/tesouro-direto/tesouro-direto/perguntas-frequentes/).

**Distinção temporal:** os pagamentos cripto são retrospectivos; o benchmark
é uma referência construída com a taxa corrente. A comparação serve para
priorizar pesquisa, não simula o Tesouro efetivamente mantido no mesmo ano
histórico e não prevê que o funding se repetirá no próximo ano.

## Mesmo favorecendo o carry, a conta não fecha

Como comparação padronizada, somei as taxas assinadas de funding, mantendo
nocional constante e sem capitalização. Isso produz um índice de remuneração,
não o caixa de uma quantidade fixa de moedas:

| Janela terminada em 07/09/2026 00:00 UTC | BTC anualizado simples | ETH anualizado simples |
|---|---:|---:|
{window_table}

As janelas de 30/90 dias são apenas descrições, anualizadas por 365/dias;
não foram escolhidas após os resultados e não são APYs previstos. A janela
principal de 365 dias estava registrada antes da consulta.

No cenário deliberadamente favorável de colocar os **US$5.000 inteiros em
nocional**, com zero fee, zero slippage e sem reservar margem adicional, o
funding padronizado do ano seria R$859 no BTC e R$637 no ETH. Até esses
valores ficam abaixo de R$2.900. Esse cenário não é executável no envelope
atual nem um limite superior universal para toda estratégia.

Na estrutura N=US$2.500, o funding anual exigido seria cerca de **23,14% do
nocional**, incluindo os custos ilustrativos e excluindo risco, câmbio,
tributação cripto e atenção. Com atenção de 2h/mês a R$50/h, sobe a **32,50%**.
O observado foi **3,35% BTC / 2,49% ETH**. Aumentar apenas o capital, mantendo
essa estrutura e essas taxas, não resolve o déficit percentual contra o
benchmark; a capacidade em tamanhos maiores não foi medida.

## Custos e câmbio

Fee spot: 10bps por lado na [tabela pública Regular User](https://www.binance.com/en/fee/trading).
Fee perp: cenário de 5bps por lado do [exemplo público Binance](https://www.binance.com/en/support/faq/detail/360033544231),
explicitamente hipotético no FAQ; tabela atual de futuros não retornou linhas.
Slippage: 5bps em cada uma das quatro pontas, hipótese de sensibilidade.
Nada disso foi rotulado como custo realizado ou como tarifa da conta do operador.

Foram calculadas 18 combinações descritivas por ativo: slippage0/5/10bps,
custo cambial total0/0,5/1% do capital e atenção0/R$1.200 por ano. Todas
continuam abaixo do benchmark. No índice de nocional constante, 1% de custo
FX derruba o saldo BTC de R$365,49 para R$109,23 e o ETH de R$254,61 para
−R$1,65, antes de impostos. A conta com quantidade fixa é ainda menor.

O hedge cripto não protege BRL/USD. Aplicando variações de câmbio ao capital
e ao saldo da conta com quantidades fixas, sem custo FX nem tributação:

| Mudança USD/BRL | Resultado BTC | Resultado ETH |
|---|---:|---:|
{fx_table}

São cenários, não variações previstas. O dólar precisaria subir aproximadamente
**10,11% no BTC / 10,55% no ETH** para igualar o benchmark, mesmo antes de
tributação cripto/FX. Essa contribuição é exposição cambial, não alpha do carry.
A PTAX utilizada é marca contábil, não spread de conversão acessível ao usuário.
[BCB, fechamento de 04/09](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do).

Também existe sensibilidade ilustrativa de imposto15% sobre o resultado total
positivo em BRL, incluindo FX; não foi determinado o enquadramento tributário
do operador ou de cada instrumento. A [Receita](https://www.gov.br/fazenda/pt-br/acesso-a-informacao/perguntas-frequentes/tributacao-offshore/perguntas-e-respostas-offshores-in-rfb-2-180-22-05-24.pdf)
distingue natureza do ativo e instituição de custódia/negociação. A decisão de
não aprofundar já aparece com imposto cripto zero, portanto não depende dessa
hipótese fiscal.

## Fidelidade, riscos e limite da conclusão

- Dois ativos fixados antes do download, uma venue, três janelas; nenhum
  threshold de entrada/saída, alavancagem ou ativo foi escolhido pelo resultado.
- 2.190 registros públicos de funding: 1.095 por ativo; zero duplicações e
  zero lacunas no calendário de8h verificado. Funding foi negativo em23,84%
  das observações BTC e26,85% ETH na janela de365dias.
- As fontes foram baixadas em07/09/2026. `fundingTime` é o momento do evento;
  `known_at` é a consulta atual. Esta evidência é Discovery, nunca prospectiva.
- As velas finais contêm campos intradiários posteriores ao corte: somente a
  abertura exatamente no corte foi usada como referência de saída. Máximas,
  mínimas, fechamento e volume posteriores foram excluídos.
- A identidade spot+short foi reconciliada com a mudança de basis. O custo
  de encerramento usa nocionais finais, que mudam com o preço das moedas.
- A maior perda apenas por preço da perna short, usando máximas diárias
  anteriores ao corte, foi US$364 BTC / US$288 ETH para essas quantidades.
  Isso não valida margem nem ausência de liquidação: manutenção, mark/fill,
  outages, contraparte e regras reais da conta continuam não modelados.
- Rendimento da margem: zero nesta estrutura. Remunerar colateral, usar
  portfolio margin ou mudar venue requer nova estrutura e nova avaliação;
  não foi presumido para resgatar o resultado.

Fonte primária dos pagamentos: [Binance Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).
Cada resposta, URL, instante de coleta e SHA256 está no pacote reproduzível.
Somas foram conferidas independentemente com Decimal; o ledger H1-H9 e os
parâmetros congelados permaneceram intactos. Nenhuma operação foi enviada.

## Consequência operacional

**REJECT nesta triagem econômica; retirar carry passivo BTC/ETH da prioridade
de pesquisa sob as premissas registradas.** G1 de deployment segue bloqueado;
a falsificação econômica one-shot foi autorizada pelo pedido atual do usuário.
Não há passagem por G1–G7, Proof, paper ou capital.

Reconsiderar apenas com mudança material verificável: remuneração sustentável
líquida substancialmente maior, benchmark efetivamente acessível mais baixo,
ou estrutura de capital/colateral diferente e mensurável. Simplesmente reduzir
fees ou aumentar o capital nesta mesma estrutura não corrige a diferença
observada. Nenhuma outra família ganhou prioridade automaticamente.
'''
(out/'FUNDING_CARRY_DECISAO.md').write_text(report,encoding='utf8')
shutil.copyfile(data/'results.json',out/'FUNDING_CARRY_RESULTADOS.json')

delta=f'''

### Funding carry — triagem econômica autorizada em 2026-09-07

O usuário pediu explicitamente para fechar a conta econômica e decidir se
vale aprofundar. Isso autoriza a falsificação barata em Discovery apesar de
G1 deployment permanecer bloqueado; não altera coleta, capital ou freeze.
Protocolo antes do download: commit `d85d75b`, em
`docs/evidence/funding_carry_screen_20260907/protocol.json`.

**Decisão: REJECT nesta triagem; carry passivo BTC/ETH sai da prioridade de
pesquisa sob a estrutura C=US$5.000, N=US$2.500 e benchmark de referência BRL.**
As taxas de funding de365dias somaram3,352476% BTC e2,487086% ETH. Mesmo a
comparação otimista N=C, custo zero, fica em R$859/R$637 contra referência
condicional de R$2.900–2.907. Não é refutação universal da classe.

Reconstrução contábil por quantidade fixa, incluindo basis por mark price e
custos ilustrativos: US$54,84 BTC / US$34,62 ETH, ou R$281,08/R$177,46 com
FX constante5,1253. Antes de imposto, FX e atenção; não são fills realizados.
O primeiro settlement foi excluído para não atribuir recebimento antes de
manter a posição. A referência do benchmark usa taxa corrente constante;
essa comparação com cripto retrospectivo prioriza pesquisa, não é retorno
histórico sincronizado do Tesouro nem previsão de funding.

Taxa anual requerida na estrutura padronizada:23,14% sobre nocional, ou32,50%
com R$1.200/ano de atenção ilustrativa. BTC/ETH ficam abaixo também nas
janelas de30/90dias pré-fixadas. Reduzir fee a zero não resgata a conta.
FX favorável não conta como alpha: seria necessária alta do USD/BRL de
10,11%/10,55% para igualar a referência antes de imposto.

Validação:2.190 registros públicos, sem duplicações/lacunas de8h; somas
Decimal, corte temporal, hashes e identidade spot+short conferidos. Campos
da vela final posteriores ao corte foram descartados. Reabertura só com
mudança material em remuneração, benchmark ou estrutura mensurável.
Resultados, cenários e fontes canônicos: `docs/evidence/funding_carry_screen_20260907/`.
Nenhuma migração adicional de runtime ou reexecução de H1-H9 foi feita.
'''
p=root/'docs/HYPOTHESES.md'
p.write_text(p.read_text(encoding='utf8')+delta,encoding='utf8')
p=root/'docs/reopen_dossiers/funding_carry_structural_v1.json'
d=json.loads(p.read_text(encoding='utf8'))
d['status']='ECONOMIC_SCREEN_REJECTED_NO_ACTIVATION'
d['economic_screen']={'protocol_commit':'d85d75b','result_path':'docs/evidence/funding_carry_screen_20260907/results.json',
                     'decision':r['decision'],'operator_benchmark_accessibility':'UNKNOWN; conditional comparison remains explicit'}
d['new_protocol']['stopping_rule']='User authorized one-shot economic screen on 2026-09-07. Screen rejected passive BTC/ETH carry under the declared structure/benchmark; no further outcome research or activation without material change. G1 deployment remains failed.'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

zip_path=out/'FUNDING_CARRY_REPRODUCAO.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in ['carry_protocol.json','carry_download.py','carry_analyze.py']:
        z.write(work/name,name)
    for path in sorted(data.glob('*.json')):
        z.write(path,'carry-data/'+path.name)
    z.writestr('COMO_REPRODUZIR.txt','Python 3.13+. Para reproduzir calculos offline: python carry_analyze.py\nPara repetir o download publico: instalar httpx e rodar python carry_download.py (fontes podem ter revisoes).\nProtocolo fixado antes de observar resultados. Nenhum script conecta conta ou envia ordem.\n')
(out/'FUNDING_CARRY_MANIFESTO.json').write_text(json.dumps({
    'zip_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),
    'results_sha256':hashlib.sha256((out/'FUNDING_CARRY_RESULTADOS.json').read_bytes()).hexdigest(),
    'data_check':'PASS','decision':r['decision'],'created_at':datetime.now(UTC).isoformat(),
    'source_manifest':manifest,
},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Delivered report, results, manifest and reproducible archive.')
