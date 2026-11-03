# Plano competitivo MOIRAE — revisão de 03/11/2026

## Decisão e alcance

Foco inicial: preparação ENEM com prática orientada e oficina de redação. Este documento atualiza as prioridades e hipóteses de produto do README; define preços e franquias planejados, inclui catálogo sandbox versão 2 para novos pedidos, preservando créditos e contratos anteriores. Não habilita cobrança ou integração externa. O PR #8 permanece draft, dependente do #7, sem merge.

Objetivo: oferecer uma experiência coerente que identifique dificuldades, proponha uma ação executável e demonstre evolução. Superioridade é uma hipótese a comprovar com usuários e avaliação pedagógica.

## Referência pública consultada

Fonte: https://descomplica.com.br/ — consulta em 03/11/2026. A oferta pública anuncia ENEM, Medicina e VIP, preparatórios Fuvest/Unicamp/UERJ, produtos separados de redação, matemática e questões, além de cursos livres, graduação, pós e empresas. No ENEM, anuncia aulas gravadas/ao vivo, questões, simulados, planejamento, assistente IA e 30 correções IA/mês; correção por professor é adicional. Preço exibido para uma opção ENEM: 12 parcelas de R$49,90, total R$598,80 e 14 meses de acesso. Não equivale a assinatura mensal cancelável.

Cursos livres: https://descomplica.com.br/cursos-livres/
Graduação: https://descomplica.com.br/faculdade/
Pós: https://descomplica.com.br/pos-graduacao/
Empresas: https://descomplica.com.br/empresas/

São alegações comerciais consultadas, não validação independente de entrega, qualidade ou resultados. Não houve acesso à área paga, compra ou auditoria de todo o catálogo. A análise da estrutura textual não substitui inspeção visual renderizada ou teste móvel.

## Lacunas verificadas do MOIRAE

A branch feat/persistent-essay-demo contém piloto local, SQLite, atividades pequenas, simulados reduzidos, cobrança sandbox e redação com avaliador fixo. Há persistência e controles de integridade, mas não correção semântica real. O dashboard é básico; personalização adaptativa, catálogo amplo e operação pública ainda precisam de entrega. Experiência no celular aprovada pelo usuário nesta conversa. Essa validação de uso não substitui medições específicas de acessibilidade, desempenho ou revisão visual de alterações futuras.

Decisão comercial do usuário: Essencial R$40/30 dias e Avançado R$100/30 dias, com 30 correções no Avançado. Para equilibrar a proposta, o Essencial passa a prever 10 correções e o conjunto de prática descrito abaixo. O sandbox agora usa R$40/10 e R$100/30 nos novos pedidos, com preço, duração e créditos gravados no contrato. Pedidos legados reconhecidos preservam as condições anteriores.

## Produto e diferenciação

| Frente | Nova prioridade MOIRAE | Evidência de conclusão |
|---|---|---|
| Entrada | Objetivo ENEM, tempo disponível e diagnóstico curto | Próxima atividade explicada; aluno consegue alterá-la |
| Prática | Resolução revisada, erros por habilidade e revisão espaçada | Erro gera item revisável; acerto posterior atualiza histórico |
| Redação | Cinco competências, trechos verificáveis, prioridades e reescrita | Correção real validada; comparação original/reescrita; progresso por competência |
| Planejamento | Sessões de 15/30/60 minutos ajustadas aos resultados | Plano usa dados reais e informa por que recomenda cada tarefa |
| Simulados | Expansão gradual para cadernos completos, tempo e revisão | Corpus suficiente e revisado; retomada e encerramento confiáveis |
| Evolução | Evolução por habilidade e próximos passos | Métricas reproduzíveis; amostras insuficientes explicitadas |
| Tutor | Ajuda contextual com orientação antes da resposta | Não revela gabarito antecipado; respostas avaliadas e custo limitado |
| Conteúdo | Catálogo editorial com origem e revisão | Publicação só após conferência; erros podem ser reportados |
| Confiança | Demonstração funcional, limites claros e atendimento | Página corresponde ao que cada ambiente entrega |

Decisão do usuário: não oferecer videoaulas em nenhum plano. O ensino será apoiado em prática, resoluções comentadas, materiais escritos e devolutivas de redação. Revisão humana não está incluída; sua eventual oferta exige equipe e operação próprias. Cursos livres, graduação, pós, B2B e concursos ficam fora do lançamento ENEM.

## Direção de arte e experiência

A arte passa a ser parte da entrega, com revisão visual obrigatória. Preservar reconhecimento MOIRAE e a base azul-escuro/verde-lima; criar linguagem própria e consistente, sem copiar fotografias, personagens ou composição exclusiva do concorrente.

- Hero: uma promessa concreta, CTA principal “Experimentar uma sessão” e demonstração real do produto.
- Composição: hierarquia tipográfica forte, espaço entre seções, contraste, imagens autorais/licenciadas e ritmo entre conteúdo editorial e interface.
- Mostrar o produto: redação anotada, comparação de reescrita e evolução com dados ilustrativos identificados. Evitar painel decorativo apresentado como funcional.
- Página: proposta → experiência interativa → método → recursos disponíveis → planos transparentes → FAQ.
- Sistema compartilhado de cores, espaçamentos, tipografia, botões, campos, cards, gráficos e estados de erro/carregamento/vazio.
- Área do aluno: próxima tarefa em destaque, continuidade fácil e linguagem simples. Feedback não depende só de cor.
- Não publicar depoimentos, aprovação, contadores ou parcerias sem evidência e consentimento.

Aceite: revisar a página pública, painel e oficina em 360, 390, 768 e 1440 px; teclado, foco, contraste e zoom 200%; nenhuma rolagem horizontal involuntária ou texto encoberto. Registrar capturas e limitações. A experiência atual no celular foi aprovada pelo usuário. Para alterações futuras, verificar regressões em dispositivo real.

## Revisão dos planos comerciais

Manter pagamento avulso de 30 dias e renovação manual como decisão atual. Preservar Mercado Pago como integração em teste.

| Recurso planejado | Free | Essencial — R$40/30 dias | Avançado — R$100/30 dias |
|---|---|---|---|
| Questões comentadas nas quatro áreas | 30/mês | Sem limite diário comercial | Sem limite diário comercial |
| Histórico e desempenho | Resultado da atividade | Histórico e evolução por área | Também análise por assunto/habilidade |
| Caderno de erros e favoritos | Não | Sim | Sim |
| Revisão espaçada e planejamento 15/30/60 min | Não | Sim | Sim, priorizado por dificuldades |
| Simulados por área e completos | Demonstração reduzida | Sim, com resoluções e análise por área | Também diagnóstico detalhado por habilidade |
| Correções de redação por IA | Não | 10 por ciclo de 30 dias | 30 por ciclo de 30 dias |
| Devolutiva nas cinco competências e marcações | Não | Sim | Sim |
| Reescrita orientada de trecho | Não | 1 rodada por correção | 2 rodadas por correção |
| Histórico de redações | Não | Sim | Sim, com evolução por competência e comparação entre envios |
| Materiais escritos revisados | Demonstração | Resumos e exercícios vinculados às dificuldades | Tudo do Essencial |
| Videoaulas | Não | Não | Não |

Os preços são decisão do usuário; 10 correções no Essencial e a distribuição dos recursos são o ajuste de produto desta revisão. O Avançado inclui tudo do Essencial. Os recursos desta tabela são escopo planejado, não declaração de disponibilidade atual.

Cada ciclo pago dura 30 dias desde a liberação do acesso, com renovação manual e créditos sem acúmulo. Uma nova avaliação completa, inclusive de texto reescrito, consome outro crédito; rodada de trecho usa a franquia própria acima e não equivale a nova correção integral. Falha técnica definitiva libera a reserva. Controles contra abuso continuam aplicáveis.

Preservar o histórico do aluno conforme retenção; ao expirar, aplicar os direitos Free. A mudança do catálogo deverá valer para novas compras, preservando condições de pedidos anteriores; versionar preço, franquias e direitos no pedido, sem recalcular concessões existentes pelo catálogo novo.

Antes da venda, medir custo por correção/reescrita, uso no limite, suporte, infraestrutura, taxas e margem. Tutor IA continua fora da franquia comercial definida: não anunciar disponibilidade ilimitada ou quantidade não estabelecida. O preço maior não dispensa validação pedagógica.

Não competir somente por preço: a comparação precisa considerar compromisso total, prazo de acesso, conteúdo e serviço incluído. Correção automatizada deve ser identificada como estimativa pedagógica.

## Ordem de execução

| Fase | Trabalho | Dependência e aceite |
|---|---|---|
| 1 — Experiência verificável | Corrigir ambiente de preview; revisar visual da landing, painel e oficina; registrar estados e acessibilidade | Preservar comportamento e segurança; aproveitar aprovação atual do usuário no celular e verificar regressões nas mudanças |
| 2 — Redação confiável | PostgreSQL com migrações; worker durável com lease; adaptador de avaliação; ledger de créditos; rubrica versionada | Avaliação remota fora da transação; retries sem cobrança duplicada; conjunto com referência humana; falhas sem perda definitiva de crédito |
| 3 — Rotina de aprendizagem | Caderno de erros, revisão espaçada e recomendações por habilidade | Conteúdo etiquetado/revisado; recomendações explicáveis; histórico reproduzível |
| 4 — Simulados e conteúdo | Ampliar corpus, cadernos e análise por área; tutor contextual com limites | Direitos documentados, revisão editorial e testes de carga; não converter acerto em TRI |
| 5 — Piloto acompanhado | E-mail real, operação, backup/restore, reconciliação, suporte e avaliação de preço | Percurso completo testado; privacidade e retenção resolvidas; vendas somente após validar entregas |

Próxima entrega concreta: fase 1. Uma nova arte isolada não conclui redesign; deve funcionar na página e na área autenticada.

## Engenharia e segurança

Manter monólito modular: identidade, conteúdo, prática, desempenho, redação e acesso/pagamentos. Não recomeçar o sistema. Migrar do SQLite antes de executar múltiplas instâncias; usar pool e migrações versionadas. Separar API e workers, com tarefas duráveis e recuperação após interrupção.

Autorizar dados e cotas no servidor; manter idempotência e operações atômicas. Tratar redação como entrada não confiável; sem ferramentas acionadas pelo texto. Segredos só no servidor. Logs sem redações ou dados pessoais. Limitar tamanho, concorrência, custo e tentativas. Medir filas, latência, falhas e consumo. Testar isolamento entre contas, expiração, duplicação e concorrência.

Manter restrição atual do piloto a maiores de 18 anos até implementar fluxo adequado de menores. Não remover os bloqueios de produção existentes por exigência comercial.

## Medição e decisões

Avaliar: conclusão da primeira sessão, retorno em sete dias, revisões realizadas, reescritas concluídas, compreensão da devolutiva, erros pedagógicos e custo por aluno ativo. Registrar denominador, período e amostra; não inventar metas de aprovação. Antes do piloto, definir critérios pedagógicos de aceitação com responsável qualificado.

## Estado desta revisão

Entregue: benchmark público e mudança documentada de estratégia, prioridade visual e sequência de implementação. Catálogo e apresentação dos planos atualizados em código. Permanecem pendentes: redesign completo, recursos pedagógicos planejados, IA real, QA renderizado desta alteração e publicação. O próximo trabalho deve partir do HEAD atual e preservar os contratos de teste.
