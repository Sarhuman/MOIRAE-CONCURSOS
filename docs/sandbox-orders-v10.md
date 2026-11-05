# Pedidos, carteira e cupom — rodada Windows de 04/11/2026

## Estado e dependências

Piloto FastAPI/SQLite de instância única. A rodada começou no HEAD remoto `6fe931ac3fff438cbc400ff2696b5256eda4ea04`, com CI aprovada (run 41948072621). Trabalho em `work/moirae-wallet-review`; checkout antigo, alterações do acervo e bancos existentes preservados. Sem WSL, OpenAI, campanha operacional, merge, deploy ou cobrança real.

Implementados anteriormente: autenticação e políticas, diagnóstico, recomendação/prática, revisões/favoritos/planejamento, simulados com cotas, acervo com fallback oficial, oficina de notas fixas, lotes/reservas/eventos, política aprovada da roleta. A suíte completa existente é a evidência de API/domínio desses percursos; não equivale a navegação visual.

Nesta rodada: contratos anexados aos mesmos `billing_orders`, concessão por pagamento verificado para a mesma carteira sandbox, cupom coordenado com pedido, exportação dos novos dados e correções de comunicação. Não existe segundo ledger nem segundo worker. Mensalidades permanecem no catálogo v3 (R$44/R$110, 10/30 créditos previstos). Planos concedem acesso; pacotes concedem apenas lotes sandbox, sem duplicar a franquia do plano. A oficina continua exigindo plano de teste ativo.

Bloqueios externos: controle do navegador bloqueado pela plataforma por incompatibilidade da fiscalização de URLs no navegador Windows selecionado; nenhuma tentativa de contorno ou nova captura. Integração externa Mercado Pago não homologada nesta rodada, sem credenciais/comprador de teste utilizados. Desktop, 360/390/430 px, teclado, foco, zoom 200%, contraste e movimento reduzido estão **pendentes de conferência real**. Regras CSS de contenção foram revisadas por código, sem afirmar validação renderizada.

## Contratos financeiros sandbox

Schema 15 aditivo: `sandbox_order_contracts` e `sandbox_coupon_holds`, ligados aos pedidos e titulares existentes. Snapshot registra produto, preço, desconto, versão e, para pacotes, quantidade/validade e cotação de origem. Valores em centavos. Pacotes 5/10/30: R$27,50/R$49,50/R$132,00, com 10% aplicado uma vez pelo cotador já existente. Nenhum juro estimado é somado ao preço validado; somente pagamento único 1x nesta integração.

`POST /api/sandbox/credit-packs/checkout` recebe apenas `product` e UUID `key`. `POST /api/billing/checkout` aceita um único `coupon_code` opcional. Autenticação, e-mail confirmado, política aceita, origem/CSRF e rate limit permanecem obrigatórios. Não há endpoint que aceite saldo, confirmação financeira, valor ou desconto do cliente. `GET /api/sandbox/credit-packs` informa disponibilidade; `/carteira` mantém botões desabilitados quando faltam requisitos.

Checkout de pacotes exige carteira habilitada, provedor sandbox e `MOIRAE_SANDBOX_PACK_VALIDITY_DAYS` explícito (inteiro de 1 a 365). Não há valor padrão: **90 dias continuam proposta**, usados apenas em fixtures. A variável é uma configuração confiável para homologação, não aprovação comercial. Sem configuração, responde 503 antes de criar pedido. Não configure como oferta pública antes de aprovar validade/termos.

O webhook existente autentica assinatura e consulta o pagamento no servidor. Verifica ID, coletor, BRL, ambiente `live_mode=false`, valor integral e referência. Notificação ou retorno do checkout não concede saldo. O pagamento não pode migrar de pedido. Snapshot, ligação do pagamento, lote e evento de concessão são liquidados na mesma transação SQLite. Origem única `billing-sandbox:<pedido>` e chave idempotente impedem duplicação. Repetição não renova a validade. Reabertura mantém dados. Eventos antigos e estados terminais não reativam lotes.

Reserva técnica de checkout: **30 minutos**, reduzida ao vencimento do cupom quando necessário. Não altera a validade do cupom emitido. Consulta dos pedidos ou nova tentativa encerra contratos pendentes vencidos; validação de capacidade ignora holds vencidos imediatamente, sem depender dessa limpeza. Pagamento aprovado depois do prazo/cancelamento vai para análise, sem concessão automática. `POST /api/sandbox/orders/{id}/cancel` encerra apenas a reserva local do titular; não cancela uma preferência nem estorna dinheiro no provedor. `/planos` oferece essa ação em pedidos pendentes.

Falha de comunicação ao criar preferência pode representar resposta perdida: pedidos protegidos ficam em análise, sem recriar preferência na mesma chave. O cupom é liberado e eventual pagamento tardio exige análise. Não há job automático de retentativa externa nem endpoint público de aprovação manual. A liberação operacional de um caso em análise ainda exige procedimento autorizado; não foi inventada uma concessão administrativa aberta.

Rejeição/cancelamento/reembolso/chargeback revogam o lote e liberam reservas abertas, preservando consumo e eventos históricos. Saldo revogado/vencido nunca volta a ser utilizável. Reembolso parcial ou crédito já consumido bloqueia o lote e marca análise monetária: **não há política inventada de devolução proporcional nem chamada automática de refund**. Regressão de estado após concessão também bloqueia o lote para análise, em vez de manter saldo gastável. Solicitação de reembolso continua sendo registro para análise, sem estorno confirmado.

## Cupom no pedido

Reutiliza `configure_approved`, a configuração versionada e os validadores existentes: 5%, chance independente 1/100, demais 99 sem prêmio/código resgatável, três meses de calendário, apenas Avançado, uma participação por conta/campanha, uso único e sem acúmulo. Nenhuma campanha operacional foi criada; datas e limite global continuam decisão pendente.

O pedido reserva cupom e capacidade global atomicamente. Holds ativos contam junto aos resgates concluídos; duas contas não ultrapassam o limite por concorrência. Cupom reservado não pode ser cotado/resgatado em outro pedido ou pelo adaptador interno isolado. Pagamento aprovado confirma o resgate e acesso em uma transação; recibo usa o preço congelado mesmo se mudar o catálogo. Cotação no navegador não reserva benefício. Repetição da mesma chave mantém pedido e desconto; troca de cupom na chave é rejeitada.

Pedido abandonado expira em 30 minutos; cancelado ou recusado libera reserva/capacidade sem alterar vencimento emitido. Pagamento tardio de uma reserva liberada não usa o cupom de outro pedido. Cupom já liquidado permanece usado após reembolso: sem segunda participação ou restauração automática. Fim da janela de participação não reduz a validade emitida; desativação explícita de campanha continua bloqueando confirmação.

## Segurança, dados e limites

Leituras e cancelamento são do titular. Exportação inclui contratos/holds, além dos lotes, eventos e recibos existentes. Exclusão de contas com pedidos continua bloqueada pelo procedimento de retenção já existente; não se apagam registros financeiros por cascata. Não foram modificados créditos reais nem o worker real, que continua separado e desabilitado sem controles próprios. Não foram usados segredos reais ou logs de credenciais.

## Roteiro Windows para Henrique (até dez passos)

1. Abra PowerShell na pasta **desta cópia isolada**, antes de executar qualquer caminho relativo. Prepare `.venv-win` conforme README.
2. Use um banco novo com `python -m backend.moirae.local_playtest` e as variáveis do roteiro [v9](windows-wallet-validation-v9.md); o preparador recusa sobrescrever bancos. Mantenha `MOIRAE_ESSAY_AI=false` e `MOIRAE_ESSAY_AI_REVIEWED=false`.
3. Inicie com `.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers`. Faça login na conta de teste preparada.
4. Em `/carteira`, confira saldo e pacotes indisponíveis sem configuração financeira. Envie pela carteira em `/redacoes`: saldo disponível reduz 1, reservado aumenta 1.
5. Gere a demonstração: reservado volta a zero, consumido aumenta 1. Atualize, reabra e repita a requisição pela interface: sem consumo duplo. A nota é fixa de demonstração.
6. Em `/planos`, confira R$44/R$110, 10/30 créditos previstos, pedidos próprios e mensagens honestas. Sem campanha aprovada/provisionada, a roleta permanece demonstrativa e não emite benefício.
7. Confira desktop e larguras 360, 390 e 430 px, Tab/Shift+Tab, Escape nos diálogos, zoom 200% e movimento reduzido. Registre capturas reais e problemas encontrados; esta etapa está pendente.
8. Execute `.\.venv-win\Scripts\python.exe -m pytest -q` e `node --test (Get-ChildItem tests\*.test.cjs | ForEach-Object FullName)` para reproduzir cenários de falha, concorrência, cupons e provedor falso sem navegador.
9. Somente em futura homologação com credenciais de teste autorizadas, HTTPS e validade sandbox explicitamente definida, habilite o provedor conforme [billing](billing-sandbox.md). Use contas/cartões de teste; confira pedido→pagamento→lote e cancelamento. Não provisione campanha sem datas/limite aprovados.
10. Não habilite cobrança real, correção OpenAI, merge ou deploy; casos monetários parciais/consumidos e homologação externa permanecem bloqueados.

## Registro de verificações

Os resultados finais desta rodada serão registrados aqui após a conclusão das execuções, sem somar testes sobrepostos. Capturas novas: nenhuma.
