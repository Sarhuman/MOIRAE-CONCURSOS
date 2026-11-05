> **Estado atual:** consulte [pedidos sandbox v10](sandbox-orders-v10.md). Este documento registra a entrega anterior; as limitações de integração de pedidos foram parcialmente resolvidas com testes de provedor falso, sem homologação externa ou venda real.

# Carteira, oficina e roleta conectadas — sandbox

## Resultado

A página `/carteira`, acessível pela conta e pela oficina, apresenta créditos disponíveis, reservados e consumidos, lotes e vencimentos, situação de revogação e até 100 eventos recentes. Não há compra ou recarga pública.

Na oficina `/redacoes`, selecione explicitamente `Carteira sandbox` em `Usar créditos de`. A opção só é habilitada quando `MOIRAE_COMMERCE_SANDBOX=true`. A fonte padrão continua sendo a franquia demonstrativa anterior; envios já salvos preservam seu comportamento.

O envio com carteira insere a redação, reserva um crédito e grava a associação em uma única transação. Conclusão consome uma vez; falha do avaliador, acesso vencido ou crédito indisponível encerra o envio e libera a reserva. Vencimento e revogação continuam bloqueando novo uso. O gerador é o `DemoEvaluator` local: notas fixas e comentários ilustrativos, sem OpenAI. O processamento real continua isolado e rejeita o campo de financiamento sandbox.

Schema v13 aditivo associa redação demonstrativa à reserva. Exportação inclui as associações; a exclusão mantém o comportamento de cascata. Os envios da carteira não descontam também a franquia demonstrativa do acesso. Ainda é necessário acesso pago de teste ativo para usar a oficina; carteira não concede acesso premium.

## Teste no Windows, sem WSL

Na raiz de um checkout atualizado, com Python do Windows e `.venv-win` preparados conforme `next-local-test.md`, execute no PowerShell. Escolha um nome de banco novo: o preparador recusa qualquer arquivo existente.

```powershell
$env:MOIRAE_ORIGIN="http://127.0.0.1:8000"
$env:MOIRAE_SECURE_COOKIE="false"
$env:MOIRAE_ESSAY_DEMO="true"
$env:MOIRAE_COMMERCE_SANDBOX="true"
$env:MOIRAE_ESSAY_AI="false"
$env:MOIRAE_ESSAY_AI_REVIEWED="false"
$env:MOIRAE_MP_SANDBOX="false"
$env:MOIRAE_DB=Join-Path $PWD "var\henrique-wallet-v7.sqlite3"
.\.venv-win\Scripts\python.exe -m backend.moirae.local_playtest --database "$env:MOIRAE_DB" --email henrique@example.test --wallet-credits 3
.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

O preparador pede uma senha de teste, sem exibi-la; os três créditos são concedidos somente no banco novo e vencem em 30 dias. Não há senha padrão, pagamento ou chamada externa. Não execute o preparador em produção.

1. Entre em `http://127.0.0.1:8000/estudar` e abra `/carteira`: saldo disponível 3.
2. Abra `/redacoes`, selecione `Carteira sandbox`, preencha tema e texto com pelo menos 100 caracteres, e envie.
3. Atualize a carteira: disponível 2, reservado 1, consumido 0.
4. Na redação salva, gere a demonstração. Atualize a carteira: disponível 2, reservado 0, consumido 1.
5. Recarregue as páginas. Texto, estado e movimentações devem permanecer. Gerar novamente não desconta outro crédito.

Falhas e concorrência são exercitadas pelos testes, sem botão público de injeção de falha ou estorno arbitrário.

## Roleta

`GET /api/coupon-experience` informa o modo público, sem cache. Sem campanha configurada e ativa, mantém demonstração sem prêmio. Se a consulta falhar, oferece apenas animação com aviso, sem emitir cupom.

Para uma campanha sandbox previamente configurada por operador confiável usando `SandboxCoupons.configure`, defina `MOIRAE_COUPON_CAMPAIGN` para seu ID e mantenha `MOIRAE_COMMERCE_SANDBOX=true`. Nenhuma campanha ou desconto é criado automaticamente. Os exemplos de probabilidades/descontos dos testes não são política aprovada.

A roleta exibe regras, resultados possíveis e pesos, validade, elegibilidade e limite global antes da participação. O checkbox de ciência é necessário; o POST exige `accepted_rules=true`, além de autenticação, verificação de e-mail e CSRF. A animação usa o resultado recebido do servidor, sem sorteio de benefício no cliente. Retentativas no backend preservam o mesmo cupom; a interface bloqueia novo giro após recebê-lo. O cupom é identificado como teste e não é aplicado a compras.

## Validação

- 197 testes Python aprovados na suíte completa.
- 15 testes Node aprovados, incluindo três testes de comportamento da roleta.
- Sintaxe dos scripts, compileall e IDs HTML verificados.
- Testes de integração cobrem reserva/conclusão, falha/devolução, rollback após erro de persistência, concorrência, retomada, fontes de crédito, vencimento/revogação, regras da campanha e isolamento do endpoint real.
- Inspeção visual desktop da carteira feita com resposta de API de teste, gerada pelo serviço sandbox e servida como fixture temporária. Captura: `evidence/wallet-v7-desktop-fixture.jpg`. O botão Atualizar e a ausência de overflow horizontal nessa largura foram conferidos. Não equivale a login/navegação autenticada no backend real.
- A prévia gerenciada não dispõe do runtime Python; o fluxo autenticado completo foi validado por TestClient. Não houve teste em celular físico, leitor de tela ou larguras móveis específicas nesta entrega. A roleta em fallback demonstrativo foi aberta e girada no navegador.

## Limites

Carteira ligada somente à oficina demonstrativa. Pagamento, compra de lotes, worker OpenAI, cupom em pedido real e tarifas efetivas do Mercado Pago continuam fora desta entrega. Nenhuma venda real, merge ou deploy.

## Política definida posteriormente

A política aprovada e o suporte a três meses de calendário estão em `coupon-policy-v8.md` (schema v14). Use a configuração versionada, mantendo o ambiente sandbox; exemplos sintéticos dos testes anteriores não substituem essa política.
