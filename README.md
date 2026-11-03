# MOIRAE
### Sua preparação para o ENEM começa aqui.

Plataforma web de estudos com questões comentadas, simulados e prática de redação. O ENEM é o foco inicial; concursos são uma possibilidade futura, fora do escopo do primeiro lançamento.

## Estado atual

Primeiro percurso funcional implementado para **piloto local**: cadastro/login/logout, atividades de até cinco questões, respostas persistentes, retomada e cota Free de 10 respostas por dia validada no servidor. Backend FastAPI com SQLite de instância única. A interface pública anterior permanece disponível.

**Execute seguindo [docs/mvp.md](docs/mvp.md)**. Esta entrega não está pronta para lançamento público: falta autenticação de lançamento, validação editorial, operação em produção e integração OpenAI/cobrança. O site hospedado anterior continua sendo a demonstração estática; o backend deste PR é executado separadamente.


## Experiência inicial

1. Conhecer a proposta e comparar planos na página pública.
2. Criar uma conta e resolver questões por área.
3. Consultar o resultado da atividade e suas resoluções.
4. Voltar para praticar diariamente.
5. Assinar para ampliar a prática, acompanhar a evolução e enviar redações.

O site deve funcionar bem no celular e no computador, com navegação por teclado, textos legíveis e estados claros de carregamento, erro e limite atingido.

## Planos propostos

Os valores abaixo são hipóteses para validação, não ofertas comerciais aprovadas. Os preços ainda não foram definidos.

| Recurso | Free | Essencial | Avançado |
|---|---|---|---|
| Questões comentadas | 10 por dia | Sem limite diário comercial | Sem limite diário comercial |
| Quatro áreas do ENEM | Sim | Sim | Sim |
| Resultado da atividade atual | Sim | Sim | Sim |
| Dashboard e histórico consultável | Não | Evolução e acertos por área | Também análise por assunto/habilidade, quando houver dados suficientes |
| Caderno de erros e favoritos | Não | Sim | Sim |
| Simulados | Demonstração reduzida | Por área e completos | Por área e completos, com análise detalhada |
| Redações corrigidas | Não | 3 por ciclo mensal | 8 por ciclo mensal |

As quatro áreas são Linguagens, Ciências Humanas, Ciências da Natureza e Matemática. Redação é uma frente própria.

### Regras propostas de uso

- Cota gratuita por conta, com renovação à meia-noite em America/Sao_Paulo.
- Consumir uma unidade quando uma resposta for aceita pelo servidor. Repetir a mesma requisição não pode consumir outra unidade; uma nova tentativa intencional conta novamente.
- Registrar respostas do Free para continuidade futura, sem liberar histórico ou dashboard ao aluno gratuito.
- Exibir a resolução somente após a resposta aceita; não enviar gabaritos antecipadamente no payload da questão.
- Créditos de redação vinculados ao ciclo da assinatura, sem acúmulo.
- Reservar crédito ao aceitar o envio; consumir na conclusão e devolver em falha técnica definitiva. Repetições da mesma requisição não duplicam reserva ou correção.
- Cancelamento mantém o acesso até o término do período pago. O retorno ao Free bloqueia recursos premium e preserva o histórico conforme a política de retenção a definir.
- Simulados respeitam a cota do plano; duração, tamanho e tratamento de tentativas interrompidas precisam ser definidos antes da implementação.
- Upgrade, downgrade, estorno e pagamento em atraso precisam de regras explícitas antes de habilitar cobrança.
- “Sem limite diário comercial” não elimina proteção contra automação abusiva.

## Redação e simulados

Decisão: correção automatizada por IA usando a OpenAI, exclusivamente no backend. Não há revisão humana incluída. Modelo, custos, prazo e preços dependem de avaliação pedagógica e operacional.

Não anunciar correção humana se ela não existir. Identificar claramente correções automatizadas e suas limitações. A rubrica e a devolutiva precisam de validação pedagógica antes da venda.

Simulados apresentam acertos e desempenho por área. Não apresentar uma nota como oficial do ENEM nem estimar TRI apenas convertendo a porcentagem de acertos.

Questões, imagens, textos e comentários precisam ter origem, permissão de uso e revisão editorial documentadas antes da publicação.

## Arquitetura proposta

Começar com um **monólito modular**, com responsabilidades claras e uma aplicação web responsiva. Não há necessidade inicial de microsserviços.

| Parte | Responsabilidade |
|---|---|
| Web pública | Apresentação, planos e conteúdo indexável |
| Área do aluno | Questões, simulados, redações e dashboard autorizado |
| API | Autenticação, autorização, regras e consumo de cotas |
| Banco relacional | Contas, questões, tentativas, assinaturas e créditos |
| Processamento em segundo plano | Correções de redação e tarefas demoradas |
| Administração | Publicação e revisão de conteúdo com acesso restrito |

Módulos sugeridos: identidade, conteúdo, prática, desempenho, assinaturas e redação. Regras de negócio independentes dos provedores de pagamento e correção.

A stack deste repositório ainda não foi escolhida. O backend do MOIRAE anterior é candidato a reaproveitamento após auditoria de contratos, segurança e manutenção; não copiar todo o sistema automaticamente.

### Segurança e integridade

- Conferir plano, propriedade dos dados e cotas no servidor em todas as operações protegidas.
- Não confiar em plano, papel, nota ou contador enviados pelo navegador.
- Aplicar consumo atômico de cotas e créditos, com idempotência e testes de concorrência.
- Isolar dados por aluno e impedir consulta a redações e respostas de outras contas.
- Confirmar cobrança por eventos autenticados do provedor, com deduplicação e reconciliação; nunca liberar acesso só pelo retorno do checkout.
- Manter segredos fora do repositório e do frontend; ocultar dados pessoais em logs.
- Separar acesso administrativo, registrar alterações sensíveis e proteger autenticação contra abuso.
- Definir coleta mínima, retenção, exclusão de conta e tratamento de dados de menores antes do lançamento.
- Ter migrações versionadas, backups com restauração verificada, limites de requisição e monitoramento de falhas.

## Etapas de implementação

| Etapa | Entrega | Critério de conclusão |
|---|---|---|
| 0 — Decisões | Stack, correção, regras dos planos e origem do conteúdo | Decisões registradas; custos e responsabilidades compreendidos |
| 1 — Web pública | Página inicial e comparação de planos | Navegação acessível em celular e desktop; nenhuma funcionalidade futura anunciada como disponível |
| 2 — Prática Free | Cadastro, login, questões e cota diária | Responder e ver resolução; limite aplicado no servidor e sem consumo duplicado |
| 3 — Recursos pagos | Direitos de acesso, histórico e dashboard | Free bloqueado na API; aluno pago acessa apenas seus dados; métricas conferidas |
| 4 — Redação e cobrança | Fluxo de correção e assinatura em ambiente de testes | Ciclo completo, falhas, cancelamento e eventos duplicados validados |
| 5 — Piloto | Conteúdo revisado e operação observável | Fluxos principais testados; backups e suporte preparados |

A etapa 3 pode usar direitos de acesso de teste; não vender assinaturas antes de validar cobrança e entregas prometidas.

## Verificação mínima por entrega

- Fluxo completo de cadastro, login, resposta e resolução.
- Tentativa de acessar dashboard premium com conta Free.
- Tentativa de acessar dados de outro aluno.
- Duas respostas simultâneas na última unidade da cota.
- Reenvio da mesma resposta sem dupla contagem.
- Renovação diária no fuso configurado.
- Redação com falha técnica sem perda permanente de crédito.
- Evento de pagamento duplicado ou fora de ordem sem concessão indevida.
- Navegação por teclado e uso em tela pequena.

## Decisões pendentes

- Stack web e quanto reaproveitar do backend anterior.
- Seleção e avaliação do modelo OpenAI; custo, prazo e rubrica versionada.
- Preços, cotas definitivas e custos por aluno.
- Tamanho dos simulados e regras para interrupção e repetição.
- Provedor de cobrança e regras para mudanças de plano.
- Política de privacidade, retenção e operação com menores.
- Catálogo inicial e direitos de uso dos materiais.

## Fora do primeiro lançamento

Aplicativo nativo, comunidade, ranking público, marketplace, expansão para concursos e infraestrutura de microsserviços.

O primeiro objetivo é validar se o aluno volta para praticar e percebe valor em acompanhar sua evolução e melhorar a redação.


## Demonstrações web preservadas

Execute conforme [DEVELOPMENT.md](DEVELOPMENT.md). A página apresenta a identidade azul-escuro/verde-lima e a oficina de redação com comentários fixos C3/C4/C5, comparação textual e rascunhos por marcação mantidos somente em memória durante a visita. Não há envio à OpenAI, nota ou persistência. Selecionar 15/30/60 minutos muda um exemplo fixo, não um plano adaptativo real.

### Extensão proposta dos planos

Free: 10 questões/dia, sem dashboard e sem correção de redação; proposta de até 3 ajudas de IA/dia vinculadas a questões. Essencial: 3 correções por ciclo e 1 rodada de reescrita de trecho por correção. Avançado: 8 correções por ciclo, 2 rodadas de reescrita e evolução por competência. Tutor pago com franquia mensal ainda a definir. Sem IA ilimitada. Essas propostas dependem de custo e validação antes da venda.

Veja [o contrato da oficina](docs/essay-workshop.md) para separar os recursos demonstrativos da integração futura.


## Conteúdo oficial do ENEM

Importador offline preparado para ENEM 2025 regular, cadernos azuis dos dois dias. O Inep retornou HTTP 503 nos downloads em 03/11/2026; **nenhuma questão oficial foi importada ainda**. O catálogo do aluno permanece autoral. Consulte [docs/inep-import.md](docs/inep-import.md) para coleta, extração em rascunho e conferência editorial. O processo não publica questões automaticamente.
