# Validação de carteira e cupons — Windows, 04/11/2026

Base: `f37b8c3`, PR #8. Checkout isolado: `work/moirae-wallet-review`; o checkout anterior e suas alterações locais não foram modificados. Sem WSL, merge, deploy, campanha operacional ou cobrança real.

## Escopo efetivamente verificado

Os testes existentes cobrem envio/reserva/conclusão/consumo, falha e liberação única, rollback de persistência, concorrência, retomada após recriar a aplicação, idempotência e rejeição de financiamento sandbox no endpoint de correção real.

Foram acrescentados dois testes HTTP: outra conta não consegue ler/processar a redação nem acessar o saldo reservado do titular; a política versionada via `configure_approved` é exercitada por contas autenticadas para vencedor, sem prêmio, repetição, bloqueio do Essencial, bloqueio de uso por outra conta, validade após fim da janela e vencimento exato. Datas e limite são fixtures de banco temporário, sem provisionamento de campanha operacional.

## Validação visual pendente

O controle nativo do navegador foi encerrado pela plataforma porque a fiscalização de URLs não é suportada no navegador Windows selecionado. Não houve contorno, capturas simuladas ou confirmação visual dos fluxos. Desktop, 360/390/430 px, teclado, zoom 200%, movimento reduzido e modal da roleta continuam pendentes.

## Conferência manual no Windows

Na pasta deste checkout, com `.venv-win` instalado e na mesma janela PowerShell:

```powershell
$env:MOIRAE_ORIGIN='http://127.0.0.1:8000'
$env:MOIRAE_SECURE_COOKIE='false'
$env:MOIRAE_ESSAY_DEMO='true'
$env:MOIRAE_COMMERCE_SANDBOX='true'
$env:MOIRAE_ESSAY_AI='false'
$env:MOIRAE_ESSAY_AI_REVIEWED='false'
$env:MOIRAE_MP_SANDBOX='false'
$env:MOIRAE_DB=Join-Path $PWD 'var\henrique-wallet-review.sqlite3'
.\.venv-win\Scripts\python.exe -m backend.moirae.local_playtest --database "$env:MOIRAE_DB" --email henrique@example.test --wallet-credits 3
.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

O preparador pede senha somente no terminal e recusa banco existente; se já foi criado, preserve-o e execute apenas o servidor. Não use senha pessoal.

1. Entre em `/estudar` e abra `/carteira`: disponível 3.
2. Na `/redacoes`, escolha `Carteira sandbox` em `Usar créditos de`, preencha o tema e pelo menos 100 caracteres e envie: disponível 2, reservado 1.
3. Gere a demonstração: reservado 0, consumido 1. Atualize ambas as páginas e reabra a redação; saldo e resultado devem permanecer, sem novo consumo.
4. Confira desktop e 360/390/430 px, foco por Tab, fechamento por Escape e retorno de foco do modal, zoom de 200% e movimento reduzido.
5. Sem campanha aprovada configurada, a roleta deve permanecer demonstrativa. Não crie campanha com datas ou limite improvisados.

Falha do avaliador e repetição de requisições são verificadas por testes; não existe botão administrativo público para induzir falha ou estornar créditos. Os cupons continuam sem integração ao checkout. Pedidos, carteira, Mercado Pago e reembolsos financeiros não foram integrados nesta rodada.

## Resultados automatizados desta rodada

- HEAD inicial `f37b8c3`: GitHub Actions execução 41894043469, sucesso em frontend, backend Windows e backend Ubuntu.
- Testes selecionados: `python -m pytest tests/test_wallet_essay_flow.py tests/test_sandbox_commerce.py tests/test_approved_coupon_policy.py -q`: 33 aprovados em 232,54 s, com um aviso de depreciação TestClient/HTTPX. Incluem os dois testes novos.
- JavaScript: `node --test tests/*.test.cjs`: 16 aprovados.
- Sintaxe de todos os scripts web e `python -m compileall -q backend`: aprovados.
- Nenhuma falha funcional comprovada; nenhuma regra de produção, preço ou integração financeira foi alterada. Esta entrega acrescenta cobertura e evidências, não ativação comercial.
- Suíte completa local do HEAD inicial: 204 aprovados em 812,97 s (13min32s), com o mesmo aviso de depreciação. Os 33 selecionados foram executados depois da adição dos dois novos testes; não são 33 testes exclusivos adicionais à suíte.
