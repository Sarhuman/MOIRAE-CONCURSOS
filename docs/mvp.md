# Primeiro percurso funcional — piloto local

## Entregue

FastAPI, persistência SQLite, hash Argon2id, sessões opacas revogáveis e cookie HttpOnly/SameSite. O token bruto fica apenas no cookie; o banco guarda seu hash. Sessões expiram em oito horas. No HTTPS, o cookie usa Secure e prefixo __Host-. Mutação exige origem exata e token CSRF, salvo cadastro/login, protegidos por verificação de origem. Não há CORS permissivo. Entradas rejeitam campos extras e os erros de validação não ecoam senhas.

Cadastro/login têm limitação persistente por conta e IP. O processo não confia em X-Forwarded-For. Corpo de requisição é limitado a 16 KiB por bytes recebidos. Limitação de conexões, timeouts de leitura, TLS e limites globais precisam existir no proxy antes de exposição externa.

A área /estudar permite criar conta de teste, entrar, sair, iniciar atividade, responder e consultar resolução. Atividades contêm até cinco questões e podem ser retomadas após recarregar, sair/entrar ou reiniciar o processo. A interface mostra o resultado da atividade atual, sem histórico agregado ou dashboard.

Cota Free: 30 questões por mês em America/Sao_Paulo, compartilhadas com simulados. A renovação ocorre no primeiro dia do mês, sem acúmulo. Cada nova tentativa intencional consome uma unidade. Repetições de requisição com a mesma chave retornam o resultado original. Reutilizar a chave com outro conteúdo gera conflito. Uma transação IMMEDIATE serializa validação, registro da resposta e idempotência. Na prática, o gabarito aparece após responder; nos simulados, somente após o encerramento. Sessões e tentativas sempre usam o usuário autenticado, nunca um ID informado pelo cliente.

12 questões autorais introdutórias em quatro áreas; não oficiais, não calibradas e ainda sem revisão editorial independente. Não equivalem a um banco de questões comercial ENEM.

## Executar em Linux/WSL

Na raiz do repositório, com Python 3.12 (versão validada):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
export MOIRAE_ORIGIN=http://127.0.0.1:8000
export MOIRAE_SECURE_COOKIE=false
.venv/bin/python -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Abra http://127.0.0.1:8000/estudar. Use o mesmo host configurado em MOIRAE_ORIGIN. Se preferir localhost, altere a origem. O modo de cookie sem Secure é exclusivo para teste HTTP local; em HTTPS, Secure é obrigatório. O arquivo var/moirae.sqlite3 guarda os dados localmente e está ignorado pelo Git.

## Verificar

```sh
.venv/bin/python -m pytest -q
node --check web/study.js
node --test tests/essay-fixture.test.cjs
```

A suíte verifica persistência, retomada, logout revogável, expiração, limites e renovação mensal, respostas erradas, isolamento entre contas, bloqueio premium, origem/CSRF, corpo grande, armazenamento de senha e concorrência/idempotência. Há aviso de depreciação do TestClient do Starlette com httpx; os testes passam, mas a migração do cliente deve ser avaliada em atualização futura.

## Estado do banco e migração

store.py contém a baseline de prática 1 e extensões aditivas de simulados 2 e contas 3, criada para banco vazio. Não é um mecanismo completo de migrações de produção. SQLite atende a um piloto pequeno de instância única com volume persistente; não há promessa de escalabilidade horizontal nesta entrega. Antes de produção: PostgreSQL, migrações Alembic revisadas, repositório equivalente com transações e restrições, testes de concorrência no PostgreSQL, backups com restauração e monitoramento. O serviço Practice concentra regras; a persistência é isolada em Store, mas a migração ainda exige implementar as consultas para o novo banco.

## Não entregue / bloqueios para lançamento público

- Entrega real de e-mail e operação de atendimento. Verificação, recuperação, exportação e exclusão já existem no piloto local, conforme docs/accounts-privacy.md.
- Política de privacidade e fluxo apropriado para dados de menores.
- Revisão editorial independente e catálogo de conteúdo de produção.
- Dashboard pago, pagamentos, upgrade e direitos premium.
- OpenAI, filas e créditos de redação; não há chamadas à API ou chave necessária.
- Banco PostgreSQL, implantação de backend persistente, TLS operacional, backups e observabilidade.
- QA manual no navegador do fluxo autenticado: a prévia gerenciada não conseguiu encontrar o runtime Python. Não contornar o ambiente; executar localmente para a verificação visual.

A página hospedada existente continua demonstrativa. Este backend Python não roda na hospedagem estática usada por aquela página. Não ligar o botão de cadastro da página publicada a um serviço inexistente. O link /estudar é funcional ao executar o backend deste PR.

## Próxima entrega

Verificar o fluxo manualmente no navegador, concluir autenticação de lançamento e preparar PostgreSQL. Depois integrar correção de redação conforme docs/essay-workshop.md, medindo qualidade e custo antes de habilitar venda.


## Simulados e cota mensal

O treino cronometrado e a redação digitada estão descritos em [docs/timed-exams.md](timed-exams.md). Acesse /simulados ao executar o backend. Cada treino usa seis questões da cota no início; não há cobrança adicional ao salvar ou alterar respostas. A versão 2 do schema cria tabelas sem apagar tentativas antigas, que continuam contando no mês em que foram registradas.
