# Carteira por lote e cupons — infraestrutura sandbox

Esta entrega não ativa vendas, não muda preços e não altera os créditos de redação existentes. É uma camada de domínio testável, separada das tabelas e do worker de correção real. A roleta pública continua sendo demonstração visual e não chama esses endpoints.

## Ativação local

No PowerShell, no ambiente de teste descrito em `next-local-test.md`, antes de iniciar o backend:

```powershell
$env:MOIRAE_COMMERCE_SANDBOX="true"
.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

O padrão é `false`: a API responde 503 para contas autenticadas quando desativada. A ativação não cria campanhas, cupons nem créditos. Exige autenticação, e-mail verificado e política aceita; POSTs usam o mesmo middleware de origem/CSRF. A flag não altera `MOIRAE_MP_SANDBOX`, OpenAI ou o checkout existente.

## Carteira

`SandboxWallet` oferece provisionamento confiável por `grant`, reserva unitária, consumo, liberação, estorno e revogação. Lotes usam chave de origem única e saldo separado em disponível/reservado/consumido; o banco exige que a soma seja igual à quantidade original e que nenhum contador seja negativo.

Reservas escolhem o lote válido que vence primeiro. O vencimento é exclusivo (`expires_at > now`). Reserva repetida com a mesma chave retorna o mesmo registro, inclusive encerrado; para nova correção é necessária nova chave. Consumo e liberação são mutuamente exclusivos; estorno só ocorre após consumo. Estornos/liberações em lote vencido ou revogado não devolvem saldo utilizável. A revogação encerra reservas abertas e bloqueia o lote. Histórico registra cada transição uma vez.

`GET /api/sandbox/wallet` retorna apenas a carteira do titular, identificada como teste. Não há endpoint público de recarga, reserva, consumo ou estorno; esses métodos são portas para um futuro adaptador confiável. Nenhuma concessão ou atualização destes lotes libera plano ou serviço real.

## Cupons

`SandboxCoupons.configure` é provisionamento confiável, sem endpoint administrativo. Não há campanha padrão nem descontos de exemplo persistidos. Requer configuração explícita de período, validade, produtos permitidos, limite global e resultados ponderados; campanhas são imutáveis, salvo desativação operacional. Alterações comerciais devem criar nova versão.

- `GET /api/sandbox/coupons/{campaign}/rules`: regras e pesos relativos antes do giro.
- `POST /api/sandbox/coupons/draw`, corpo `{ "campaign": "id-aprovado" }`: sorteio por `secrets.randbelow` no servidor; uma participação persistente por conta/campanha, sem nova chance após vencimento.
- `POST /api/sandbox/coupons/quote`, corpo `{ "code": "TEST-...", "product": "essencial" }`: cotação sem pedido ou débito. Rejeita campos de preço enviados pelo cliente.

O preço vem de `PLANS`, que já contém o acréscimo aprovado de 10%; ele não é reaplicado. Desconto percentual usa pontos-base inteiros e arredondamento para baixo em centavos. A cotação informa versão do catálogo, moeda e `checkout_available=false`. Não calcula juros do parcelamento nem altera a proposta de tarifas existente.

`redeem` é método interno de teste: valida titular, produto, vencimento, campanha ativa, uso único e limite global dentro de transação. Preserva recibo e preço por referência idempotente. Não cria pedido Mercado Pago, não concede acesso e não deve ser exposto diretamente ao navegador. Não há acúmulo de cupons por recibo. Uma compra futura precisará coordenar reserva/cancelamento de cupom com o estado financeiro; este método isolado não implementa tal fluxo.

## Segurança, dados e operação

Schema v12 aditivo (v11 cria a infraestrutura; v12 preserva contagem global de uso); tabelas `sandbox_*` separadas. Transações SQLite `BEGIN IMMEDIATE` serializam disputa por saldo e por limite de campanha; índices apoiam consultas por usuário, lote e campanha. Continuamos no piloto de instância única. Migração para Postgres e concorrência distribuída exigem outro contrato transacional.

A contagem global da campanha é monotônica e agregada, sem identificador do titular; excluir uma conta não repõe usos já realizados. A migração preenche a contagem a partir dos recibos existentes e pode ser repetida sem duplicá-la.

Exportação autenticada inclui lotes, reservas, eventos e cupons do titular. Exclusão de conta sem pedidos remove os dados sandbox por cascata. Registros financeiros reais preservam a política de retenção anterior. Não publique o banco ou códigos de cupons nos logs.

## Validação e pendências

Testes cobrem vencimento, FEFO, idempotência, reserva concorrente, disputa consumo/liberação, estorno, revogação, isolamento, reinício, sorteio concorrente, limite global, recibos, preço do servidor, origem/CSRF, exportação e exclusão. Valores de desconto dos testes são fixtures sintéticas, não política comercial aprovada.

A CI passa a executar backend em Windows e Ubuntu. Isso verifica portabilidade automatizada, não substitui teste manual no Windows do Henrique.

Faltam política comercial aprovada, integração da roleta a campanhas reais, adaptador de pedidos/pagamentos/refundos, carteira na interface e integração ao consumo do worker. Nada disso está anunciado como ativo.
