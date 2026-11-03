# Portfólio, proposta comercial e tarifas — revisão 03/11/2026

## Referência e decisão

A oferta pública do Descomplica foi consultada novamente: planos ENEM, Medicina e VIP; produtos separados de redação, matemática e questões; vestibulares, cursos livres, graduação, pós e empresas. No ENEM, a página anuncia 12 parcelas de R$49,90, total R$598,80 por 14 meses; correções por IA e créditos adicionais de professor são serviços distintos. Não houve compra, acesso à área paga ou validação independente de qualidade. A tentativa de renderizar o domínio diretamente no Chromium retornou ERR_EMPTY_RESPONSE; a avaliação usou as páginas públicas recuperadas.

Fontes: https://descomplica.com.br/ e páginas de cursos livres, faculdade, pós e empresas acessadas a partir dela. Não copiamos marca, textos comerciais ou ilustrações do concorrente.

Decisão do usuário: Mercado Pago será o provedor; juros do parcelamento ficam com o comprador; acrescentar 10% aos preços. Interpretado como acréscimo único de 10%, inclusive quando a compra é parcelada, sem cobrar 10% uma segunda vez em cada parcela. Não equivale a margem líquida de 10%: processamento, IA, infraestrutura, tributos e suporte permanecem custos da operação.

## Implementado

- Novo template orientado a catálogo: faixa de entrada, navegação por trilhas, portfólio filtrável, comparação de ciclos e simulador de créditos/parcelas, preservando as artes v3.
- Biblioteca aberta com seis trilhas e 18 lições: conceito, exemplo e exercício comentado. Matemática, redação, linguagens, natureza, humanas e estratégia. Conteúdo autoral introdutório em revisão editorial; sem certificação ou promessa de nota.
- Progresso das amostras apenas no navegador, com opção de limpar; sem vínculo com conta ou débito da cota de prática.
- Manifesto comercial público e simulador somente de leitura no backend e frontend. Nenhuma simulação cria pedido, pagamento ou concessão.
- Catálogo mensal sandbox versão 3: Essencial R$44/30 dias/10 créditos e Avançado R$110/30 dias/30 créditos. Novos pedidos usam esses valores; pedidos anteriores continuam usando seus próprios snapshots. Checkout mensal limitado explicitamente a 1x nesta fase.

## Preços do produto

| Produto | Base anterior ao acréscimo | Preço com 10% | Acesso/franquia proposta |
|---|---:|---:|---|
| Essencial, 1 ciclo | R$40 | R$44 | 30 dias; 10 correções |
| Essencial, 6 ciclos | R$216 | R$237,60 | 180 dias; 10 a cada 30 dias |
| Essencial, 12 ciclos | R$408 | R$448,80 | 360 dias; 10 a cada 30 dias |
| Avançado, 1 ciclo | R$100 | R$110 | 30 dias; 30 correções |
| Avançado, 6 ciclos | R$540 | R$594 | 180 dias; 30 a cada 30 dias |
| Avançado, 12 ciclos | R$1.020 | R$1.122 | 360 dias; 30 a cada 30 dias |
| 5 créditos avulsos | R$25 | R$27,50 | Compra única; validade proposta 90 dias |
| 10 créditos avulsos | R$45 | R$49,50 | Compra única; validade proposta 90 dias |
| 30 créditos avulsos | R$120 | R$132 | Compra única; validade proposta 90 dias |

Os preços de 6/12 ciclos e os avulsos são propostas, sem checkout. O desconto de pacote é 10%/15% sobre repetir o preço mensal já reajustado. Ciclo tem 30 dias: 12 ciclos são 360 dias, sem chamar esse período de um ano civil. Franquias não são liberadas todas no início e não acumulam. A validade de avulsos ainda precisa integrar termos e operação; não há carteira avulsa funcional nesta entrega.

## Tarifa Mercado Pago e parcelamento

Fonte oficial: https://www.mercadopago.com.br/ferramentas-para-vender/check-out — bloco Taxas consultado em 03/11/2026. A página informa processamento: crédito D0 4,98%, D14 4,48%, D30 2,95%; Pix 0,99%; boleto R$3,99. O FAQ da mesma página traz números divergentes para crédito, e outras páginas públicas exibem valores anteriores. O manifesto identifica a data, a fonte e essa divergência. Confirmar a conta em Seu negócio → Custos → Checkouts antes de configurar cobrança real.

O bloco público de parcelamento informa: 2x 2,53%; 3x 4,62%; 4x 6,69%; 5x 8,66%; 6x 9,96%; 7x 11,24%; 8x 12,50%; 9x 13,73%; 10x 14,93%; 11x 16,12%; 12x 17,28%, além de faixas até 18x. Esses números são referência, não cotação individual garantida. A aplicação mantém recomendações até 12x e não confunde processamento do vendedor com juros do comprador.

Simulação usa preço com markup × taxa pública da faixa como hipótese de acréscimo financeiro, arredonda para cima em centavos e distribui o total sem perder centavos entre parcelas. Exemplo: Essencial 12 ciclos, produto R$448,80; referência 12x 17,28% → custo estimado R$77,56 → total estimado R$526,36; 4 parcelas de R$43,87 e 8 de R$43,86. Não é oferta confirmada do Mercado Pago.

API devolve estimated_buyer_total_cents separado de buyer_total_cents. Para mais de 1 parcela, o valor definitivo fica null e provider_quote_required=true. Nunca usar a estimativa para cobrar ou para validar webhook. Pagamento real exige cotação e condições da conta; não há configuração de parcelado vendedor assumida pela aplicação. Não prometer sem juros. Guia oficial: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/additional-settings/payment-methods .

Recomendação: mensal em 1 pagamento; pacotes de 6 ciclos em até 6x; 12 ciclos em até 12x; crédito de 30 correções em até 3x. Aprovação, valor mínimo da parcela e demais condições dependem do provedor.

## Próximas entregas necessárias

1. Carteira avulsa separada da franquia do plano; reserva por lote, prioridade de consumo, validade, estorno e auditoria.
2. Contrato de pacote longo com alocações por ciclo, acesso, cancelamento e reembolso; sem conceder toda a franquia no início.
3. Cotação efetiva do Mercado Pago, confirmação da modalidade parcelado comprador, taxas da conta e conciliação dos valores confirmados.
4. Revisão pedagógica das amostras, catálogo maior e operação de correção real antes de vender.
5. Só então aprofundamentos por objetivo e novas trilhas, apoiados em conteúdo revisado. Não anunciar graduação, pós, mentoria humana ou videoaulas inexistentes.

## Verificação

Testes de cálculo monetário, markup único, soma exata de parcelas, limite de ciclos, valores estimados separados de cotação definitiva, simulação sem efeitos financeiros e preservação de pedidos versão 2. Testes Node verificam a mesma fonte de preços. Biblioteca validada quanto a estrutura e IDs separados do banco de prática.

Chromium: 360/390/768/1440, sem overflow, zoom de layout CSS 200%, filtros do portfólio, escolha de ciclos, estimativa 12x, leitura da biblioteca, acerto de exercício e persistência após recarga. Questão de demonstração e oficina continuam funcionando sem exceções JS. Sem teste de compra real, celular físico, aprovação jurídica/pedagógica ou publicação.
