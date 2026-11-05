> **Registro histórico:** a base foi consolidada na `main`. Para nova execução, consulte [o índice atual](README.md), [pedidos v10](sandbox-orders-v10.md) e [triagem v11](order-review-v11.md). Não trate a branch/draft abaixo como estado atual após a integração.

> **Estado atual:** consulte [pedidos sandbox v10](sandbox-orders-v10.md). Este documento registra a entrega anterior; as limitações de integração de pedidos foram parcialmente resolvidas com testes de provedor falso, sem homologação externa ou venda real.

# Prompt de continuidade — somente pendências

Trabalhe em Sarhuman/MOIRAE-CONCURSOS, branch feat/persistent-essay-demo, PR #8. Confira o HEAD e leia docs/review-fixes-v5.md antes de alterar. Ambiente do Henrique: Windows nativo, PowerShell, .venv-win; sem WSL. Preserve mudanças locais. Não faça merge nem deploy.

As correções de simulado/cota, diagnóstico, fallback do acervo, teste de migração e cobertura da CI já foram implementadas. A landing ganhou refinamento visual e uma roleta exclusivamente demonstrativa. Não refaça essas entregas.

1. Valide no Windows os comandos de docs/next-local-test.md, cadastro/verificação de e-mail e login. Use dados de teste; não exponha senha ou tokens. Teste a coleta real do acervo com curl.exe, confira falhas e confirme fonte oficial quando não existir cópia local.
2. Valide os fluxos autenticados no navegador e a landing em 360, 390 e 430 px, zoom 200%, teclado e movimento reduzido. Confira o modal com conteúdo rolável, fechar/Escape/retorno de foco e ausência de rolagem horizontal. Registre capturas reais e diferencie emulação de celular físico.
3. A infraestrutura sandbox da carteira e dos cupons foi acrescentada em docs/sandbox-commerce-v6.md (schema v12, serviços e APIs limitadas). Leia antes de implementar e não duplique. A interface da carteira, o financiamento da oficina demonstrativa e a roleta conectável ao servidor foram entregues em docs/wallet-essay-flow-v7.md. Não os duplique. Falta integrar pedidos, reembolsos financeiros e worker real. A política agora está aprovada e implementada em docs/coupon-policy-v8.md: 5%, chance 1 em 100, três meses corridos desde o giro vencedor, somente Avançado. O servidor mantém 99/100 sem prêmio, sem código resgatável. Não invente novas condições nem duplique sorteio, persistência ou validações já existentes. Use configure_approved para provisionar uma campanha sandbox, com janela de participação e limite global aprovados separadamente; não ative produção. Preserve CSRF, rate limit e integridade dos preços.
4. Com acesso autorizado à conta Mercado Pago e credenciais sandbox configuradas fora do Git, confirme tarifas/parcelamento do comprador e integração do cupom no checkout de testes. Preserve os preços aprovados, o acréscimo único de 10% e snapshots de pedidos anteriores. Não ative cobrança real. Registre qualquer regra ainda não suportada em vez de anunciar funcionamento.
5. Confira a nova execução de CI no HEAD, atualize a descrição do PR com evidências efetivas e mantenha draft. Não substitua testes de comportamento por expectativas que escondam regressões.

Entregue causa/correção de qualquer falha nova, testes e capturas, limitações e instruções de teste no Windows.
