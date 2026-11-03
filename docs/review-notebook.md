# Caderno de erros e favoritos

## Entrega

`/caderno` consulta respostas reais aceitas na prática. Os filtros mostram questões com erro anterior, favoritos ou todas as respondidas. Cada questão aparece uma vez, com a última alternativa e indicação de acerto recente; um acerto posterior não apaga o erro anterior. Resolução abre sob demanda. Consulta e favoritos não criam tentativas nem consomem cota.

API: GET `/api/review?view=errors|favorites|all`; POST `/api/review/{question_id}/favorite` com booleano estrito `enabled`. A gravação define estado explicitamente, permitindo repetição sem duplicação. Ambos exigem aluno verificado, termos aceitos e plano pago ativo no servidor. Escritas exigem origem, CSRF e rate limit. Não é possível favoritar uma questão sem resposta própria aceita nem consultar gabaritos de questões inéditas pelo caderno.

Schema aditivo 7: favoritos por aluno/questão, exclusão em cascata com a conta e índice para histórico de prática. Exportação autenticada inclui favoritos. Expiração bloqueia consulta sem apagar o histórico. A consulta SQL deduplica e limita a resposta a 100 questões, com total e limite explícitos. Dados renderizados com textContent, sem HTML do conteúdo.

## Limites

Simulados não integram esta primeira versão. A revisão é leitura de respostas anteriores; responder novamente continua sendo uma tentativa normal em /estudar. Ainda não há agenda de revisão espaçada nem plano adaptativo. A lista mostra até 100 questões, sem paginação nesta versão; expansão do catálogo deve incluir paginação antes de ultrapassar esse limite.

## Apresentação

Página inicial com nova chamada, hierarquia e acabamento do cartão de sessão, oficina e planos; painel com acesso ao caderno e ações de continuidade. O caderno tem estados de carregamento, vazio, falha/repetição e filtros operáveis por teclado. Cores não são a única indicação de acerto ou favorito.

## Validação

Testes HTTP/domínio cobrem resposta real, isolamento, plano vencido, ausência de autenticação, origem, CSRF, entrada estrita, idempotência, concorrência, persistência, exportação e erro preservado após acerto. Verificação de sintaxe JavaScript e testes existentes da oficina executados.

Revisão renderizada não concluída: tentativa de instalar Chromium falhou com arquivo de download inválido/truncado. Validar 360/390/768/1440 px, foco, zoom e regressões de interação antes de considerar QA visual concluído. A aprovação móvel anterior do usuário não é evidência para esta nova alteração.

Sem publicação, merge ou cobrança real. Redação continua demonstrativa.
