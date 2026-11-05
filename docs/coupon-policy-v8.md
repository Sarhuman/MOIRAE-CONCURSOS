> **Estado atual:** consulte [pedidos sandbox v10](sandbox-orders-v10.md). Este documento registra a entrega anterior; as limitações de integração de pedidos foram parcialmente resolvidas com testes de provedor falso, sem homologação externa ou venda real.

# Política de cupom aprovada em 04/11/2026

Definição do Henrique, registrada em `data/coupon-policies/avancado-5-v1.json`:

| Regra | Valor |
| --- | --- |
| Desconto vencedor | 5% |
| Chance por giro | 1 em 100 (1%) |
| Sem prêmio | 99 em 100 (99%) |
| Validade do cupom | 3 meses corridos desde o giro vencedor |
| Produto elegível | Somente Avançado |

Uma participação por conta/campanha, uso único e sem acúmulo permanecem como regras já existentes. A chance é independente em cada giro; não há garantia de um ganhador em cada grupo de cem participantes.

## Implementação

`SandboxCoupons.configure_approved(campaign, starts_at, ends_at, max_uses)` carrega a política versionada. Janela de participação e limite operacional global continuam parâmetros explícitos do operador: não foram inventados a partir da decisão sobre desconto e probabilidade. Não há nova campanha criada automaticamente nem ativação de produção.

Exemplo de chamada interna: `coupons.configure_approved(campaign_id, inicio_aprovado, fim_aprovado, limite_global_aprovado)`. Em seguida, o ambiente de teste pode apontar `MOIRAE_COUPON_CAMPAIGN` ao ID, com `MOIRAE_COMMERCE_SANDBOX=true`. Não há endpoint público administrativo. Não copie a política dos testes anteriores: ela usa benefícios sintéticos diferentes.

O sorteio escolhe uniformemente um dos 100 bilhetes no servidor: um bilhete concede 500 pontos-base (5%), os outros 99 não concedem prêmio. A participação sem prêmio é persistida para impedir novo giro, mas a resposta não entrega código e o servidor recusa sua cotação ou resgate. A interface informa “não houve prêmio”, sem exibir cupom de 0%.

## Três meses de calendário

Schema v14 acrescenta `valid_months`; campanhas anteriores permanecem com seu prazo em segundos. A validade nova usa o calendário de Brasília (`America/Sao_Paulo`) e preserva o horário do giro. Se o mês de destino não tiver o mesmo dia, usa o último dia desse mês.

- Giro em 04/11/2026 às 10h30: vence em 04/02/2027 às 10h30.
- Giro em 31/01/2026 às 10h30: vence em 30/04/2026 às 10h30.
- Giro em 30/11/2027 às 10h30: vence em 29/02/2028 às 10h30.

O fim da janela de participação não encurta a validade de um cupom já emitido. A desativação operacional explícita da campanha continua bloqueando uso. O prazo é exclusivo: no instante de vencimento o cupom já é inválido.

No catálogo atual de R$110 para o Avançado, a cotação sandbox resulta em R$5,50 de desconto e R$104,50 no produto. Não inclui juros ou cotação definitiva de parcelamento. Essencial, créditos avulsos e demais produtos não são elegíveis.

## Verificação

Testes determinísticos percorrem o espaço completo de 100 bilhetes (sem simular uma garantia estatística), verificam não ganhador sem cupom, repetição do resultado, restrição ao Avançado, preço, validade após fim de participação, limite exato de vencimento, virada do ano, ano bissexto, fim de mês e migração de campanhas legadas. O teste da interface confere 5%/1 em 100, 99 em 100 sem prêmio e três meses corridos.

Checkout e pagamento real continuam desativados. Esta entrega registra e testa a política, sem publicar a campanha em produção.
