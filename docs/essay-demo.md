# Oficina persistente de demonstração

## Executar

No backend local, habilite `MOIRAE_ESSAY_DEMO=true` e abra `/redacoes` na mesma origem. A flag é falsa por padrão. O envio exige conta verificada, termos aceitos e concessão de plano pago ativa do piloto. As concessões continuam sendo criadas pelo fluxo sandbox de pagamentos; não existe endpoint para autoatribuição de plano. Os testes usam provedores falsos e registros exclusivamente sintéticos.

A hospedagem estática existente não executa este backend Python. Esta entrega permanece em branch/PR; não habilita vendas nem OpenAI.

## Percurso e API

- `GET /api/essays`: saldo de demonstração e até 100 envios recentes, sem corpos dos textos.
- `POST /api/essays`: `{key: UUID, theme: 3..200 caracteres, text: 100..4000 caracteres}`. Cria versão imutável e reserva uma unidade da franquia de demonstração.
- `POST /api/essays/{id}/process`: execução explícita do avaliador local; permite retomar um envio após reiniciar o processo. Sem fila ou trabalho em segundo plano.
- `GET /api/essays/{id}`: texto original, resultado, estado e versões de reescrita do proprietário.
- `POST /api/essays/{id}/rewrites`: `{key: UUID, annotation_id, text: 20..1200 caracteres}`. Até dez versões por envio, sem nota ou crédito adicional.

As mutações exigem sessão, origem e CSRF. UUID é identificação, não autorização: todas as leituras verificam o proprietário. Reutilizar uma chave com outro conteúdo retorna conflito. A mesma chave conserva o envio original, inclusive após expiração do acesso; não cria uma nova avaliação. O histórico próprio continua legível após expiração do plano. Reescritas de resultados existentes são um exercício local, sem custo de IA, permitido após expiração.

## Resultado e créditos

Todas as notas são **fixas em 120 por competência**, marcadas como demonstração, sem avaliação pedagógica do texto. O primeiro trecho recebe uma orientação ilustrativa de C3. O modelo não é chamado e não há geração de feedback semântico. A reescrita é guardada e exibida junto do original, sem afirmar melhora.

Novas concessões de teste recebem 10/30 créditos Essencial/Avançado. Concessões antigas preservam 3/8; o saldo usa a franquia gravada na concessão, não o catálogo atual. Os registros de demonstração não alteram `access_grants.essay_credits` e não serão o ledger de correções reais. Envios `received` e `processing` reservam uma unidade; `completed` consome a unidade de teste; `failed` libera a reserva. Não há acúmulo entre concessões. Transações SQLite `IMMEDIATE` impedem reserva duplicada e ultrapassagem do saldo. Falhas são terminais para aquele envio e não disparadas novamente por repetição de HTTP; um novo envio usa uma nova chave.

O processamento valida o acesso antes de executar. Erro técnico, resultado malformado e acesso expirado não produzem nota zero. Erros internos são substituídos por códigos genéricos; não retornam textos de exceção.

## Contrato e privacidade

`backend/moirae/essays.py` contém os modelos estritos e as invariantes. `data/essay-demo-schema.json` é o schema versionado **do avaliador demonstrativo**, não o contrato final do provedor OpenAI. `data/essay-demo-fixture.json` contém exemplo autoral para testes sem rede. Exatamente cinco competências distintas, notas em passos de 40, IDs de marcação únicos, intervalos UTF-16 com fim exclusivo e correspondência literal com o texto são validados antes da persistência. Não alterar o original após gerar posições.

A UI usa elementos DOM e `textContent`, nunca HTML retornado pelo avaliador. Texto e reescritas ficam no banco local, entram na exportação autenticada e nas regras de exclusão da conta. Contas com pedidos continuam bloqueadas para exclusão automática pela pendência anterior de retenção financeira; esta entrega não resolve esse bloqueio. Não há transmissão externa, OCR, anonimização garantida ou logs adicionais do corpo dos textos. Os limites de 16 KiB por requisição também se aplicam: textos com muitos caracteres multibyte podem atingir esse teto antes de 4.000 caracteres.

## Evolução para IA real

O avaliador local executa dentro de uma transação curta. **Nunca substituir por uma chamada de rede dentro dessa transação.** Implementar fila durável, worker com lease, recuperação de tarefas abandonadas, timeout e ledger separado antes do adaptador OpenAI. O estado `processing` atual é transacional e não observável como job assíncrono durável. Falta o contrato do avaliador real, rubrica validada, política de dados e avaliação humana de referência. Recusas e saídas truncadas reais não foram testadas com provedor: nesta entrega são cobertas apenas falha sintética e saída inválida.

## Validação

Testes cobrem fluxo HTTP, retomada após reinício, exportação, restrições de conta, CSRF, isolamento, expiração, concorrência, idempotência, falha técnica/validação com liberação de reserva, Unicode/offsets, limite de versões e migração aditiva. QA visual de navegador e dispositivos reais permanece pendente.

## Revisão de interface

Marcações têm cores e rótulos C1–C5, seleção pelo teclado e lista de trechos. Segmentação por offsets preserva sobreposições sem descartar texto. Comparação mostra o trecho original associado à versão escolhida, lado a lado em tela ampla e empilhado no celular. Rascunhos de reescrita são mantidos em memória por redação e marcação, sem localStorage; falhas preservam texto e chave idempotente. Fechar/recarregar com alterações não enviadas aciona o aviso nativo do navegador quando permitido. Não é recuperação durável: a interface informa a perda ao fechar a aba. Durante envios, campos são bloqueados para evitar sobrescrever edições feitas enquanto a resposta chega. Nenhuma avaliação semântica foi acrescentada.

