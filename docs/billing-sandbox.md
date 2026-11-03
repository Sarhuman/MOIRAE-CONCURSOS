# Planos, acesso e Mercado Pago — somente sandbox

## Escopo entregue

Catálogo no servidor: Essencial R$ 40,00 por 30 dias com 10 créditos previstos de redação; Avançado R$ 100,00 por 30 dias com 30 créditos. Pagamento avulso e renovação manual. Não há assinatura recorrente. O prazo começa quando a confirmação é processada e o acesso liberado. Créditos são uma alocação por período; ainda não há correção OpenAI ou consumo desses créditos.

/planos mostra preços, pedidos próprios e botão de teste quando o adaptador estiver configurado. /painel entrega contagem de respostas/acertos, desempenho por área, últimas 20 tentativas e total de simulados encerrados para conta com acesso pago ativo. Este é um painel básico, não a análise avançada completa anunciada como proposta futura.

## Estado do checkout

Desabilitado por padrão. Não houve chamada real ao Mercado Pago, compra com usuário de teste, cobrança, devolução financeira ou validação ponta a ponta com o provedor. Testes usam FakeProvider injetado no backend; não há endpoint público de aprovação simulada.

Adaptador HTTP preparado para Checkout Pro via Preferences API e consulta GET /v1/payments/{id}. Apenas sandbox; live_mode=true nunca concede acesso. Uma origem HTTPS e credenciais de teste reais são necessárias para o ensaio integrado. Não use credenciais ou cartões de produção.

Variáveis de ambiente, sem segredos no Git ou navegador:

- MOIRAE_MP_SANDBOX=true para habilitar o adaptador de teste.
- MOIRAE_MP_ACCESS_TOKEN: credencial da conta de teste apropriada ao Checkout Pro.
- MOIRAE_MP_COLLECTOR_ID: ID numérico do vendedor de teste.
- MOIRAE_MP_WEBHOOK_SECRET: assinatura secreta configurada na aplicação, com pelo menos 32 caracteres nesta integração.
- MOIRAE_ORIGIN: origem HTTPS validada para o ambiente de testes.

Em HTTPS o cadastro público também exige entrega de e-mail, ainda pendente. Não contornar esses bloqueios para vender.

## Fluxo e invariantes

1. Conta autenticada, com e-mail verificado e termos aceitos, escolhe o plano.
2. Servidor cria pedido com preço e plano do catálogo; cliente envia só o ID do plano e chave idempotente.
3. Preferência recebe external_reference do pedido e URLs fixas do servidor. O retorno usa sandbox_init_point validado.
4. Webhook é a única exceção exata à exigência de Origin do navegador; o corpo continua limitado e a assinatura é obrigatória.
5. Validar x-signature via HMAC-SHA256 do manifesto id:<data.id>;request-id:<x-request-id>;ts:<ts>;, com janela de cinco minutos. Aceita timestamp em segundos ou milissegundos. Exige concordância do ID do corpo e da query.
6. Consultar o pagamento no Mercado Pago. Conferir ID, external_reference, valor exato em centavos, BRL, collector_id e live_mode=false. Não confiar no status recebido no corpo da notificação ou na URL de retorno.
7. Approved concede uma única alocação de 30 dias por pedido. Repetições não prolongam acesso nem duplicam créditos. Datas antigas do provedor não desfazem estado novo.
8. Pagamento pendente não concede acesso. Reembolso, estorno, chargeback ou reembolso parcial revogam o direito; mudanças intermediárias suspendem até reconciliação válida. Estados revogados não são reativados automaticamente por evento posterior.
9. Um pedido em aberto por aluno e bloqueio de compra durante acesso ativo evitam períodos sobrepostos neste MVP. Outro pagamento aprovado que sobreponha um direito existente vai para needs_review; requer operação humana ainda não implementada.

A renovação antecipada, troca de plano, múltiplos pagamentos para o mesmo pedido, falhas de timeout com preferência possivelmente criada e conciliação de eventos perdidos exigem fluxo operacional antes de liberar produção. Solicitação de início em falha pode exigir nova chave; não há cancelamento automático de preferências órfãs.

## Permissões e cota

O servidor confere o prazo em cada consulta: vencido ou revogado volta ao Free, sem confiar no plano enviado pelo navegador. Prática paga grava free_charge=0; simulados iniciados durante o acesso pago debitam zero questões da cota Free. Uso gratuito anterior continua contando no seu mês. Um simulado iniciado no Free mantém o débito original mesmo se a conta se tornar paga depois.

A extensão de schema 4 preserva tentativas anteriores com free_charge=1. A migração ainda é específica do SQLite de piloto, não migração PostgreSQL de produção.

## Cancelamento e direitos

O formulário registra solicitação de arrependimento/cancelamento, com senha e CSRF. Dentro dos sete dias iniciais desde a liberação, marca a janela inicial; pedidos posteriores também são aceitos para análise, sem negar outros direitos legais. Esse cálculo técnico precisa de revisão jurídica das condições e da contagem antes da oferta pública.

**Registrar solicitação não executa estorno.** Não há chamada ao endpoint de reembolso nem prazo operacional prometido. O acesso é revogado quando a consulta ao provedor confirma reembolso/contestação. Não vender antes de existir atendimento e processamento real de cancelamento/reembolso.

Contas com pedidos não usam a exclusão automática do piloto; retornam orientação sobre análise de retenção. Exportação inclui seus pedidos sem credenciais. É necessário implementar atendimento de direitos, anonimização adequada e retenção fiscal antes de receber dados ou pagamentos reais.

## Validação antes de produção

Testes locais cobrem preços, checkout desabilitado, idempotência, concorrência, assinatura, IDs divergentes, valor/moeda/vendedor/modo incorretos, status pendente, concessão única, prazo, revogação, suspensão, uso pago separado do Free, isolamento e bloqueio de destinos externos.

Ainda faltam: ensaio integrado com Mercado Pago e usuários de teste; conciliação e tarefas de reprocessamento; operação de reembolso; entrega de e-mail; LGPD e termos completos; correção OpenAI; revisão visual de navegador/celular e infraestrutura persistente de produção. O site hospedado é estático e não executa este backend.

## Documentação oficial consultada

- https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro-preferences/create-preference/post
- https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro-preferences/get-payment/get


## Catálogo versionado

Novos pedidos usam versão 2: Essencial R$40/10 créditos e Avançado R$100/30 créditos, ambos por 30 dias, sem videoaulas. O pedido guarda preço, créditos, duração e versão antes de abrir checkout. Reconciliação usa esse contrato, nunca a franquia atual do catálogo. Schema 6 migra apenas pedidos legados reconhecidos R$35/3 e R$55/8 para versão 1; concessões existentes não mudam. Pedidos sem contrato reconhecido exigem revisão e não concedem acesso. A oficina segue demonstrativa, sem correção real.
