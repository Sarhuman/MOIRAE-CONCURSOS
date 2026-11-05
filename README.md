# MOIRAE

**Preparação para o ENEM com prática, revisão e escrita.**

[![Testes](https://github.com/Sarhuman/MOIRAE-CONCURSOS/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Sarhuman/MOIRAE-CONCURSOS/actions/workflows/ci.yml)

<img src="web/art/study-hero-v1.webp" alt="Ilustração original do MOIRAE: jovens estudando entre livros e formas coloridas." width="760">

Este repositório contém o **piloto web local** do MOIRAE: FastAPI, SQLite de instância única e interface HTML/CSS/JavaScript. O foco inicial é o ENEM, sem videoaulas. O antigo projeto Flutter `Sarhuman/MOIRAE` é independente.

**Estado: desenvolvimento e sandbox.** A integração interna de pagamentos usa testes automatizados; não houve homologação externa com comprador Mercado Pago. Correção real por IA e vendas reais permanecem desativadas. Integrar código à `main` não publica o site nem libera o serviço comercial.

**Acesso às questões:** cadastro e login são obrigatórios, tanto no Free quanto nos planos pagos. Não é necessário assinar para usar o Free. A página pública apresenta o produto; perguntas, exercícios, biblioteca e acervo ficam na área cadastrada, com confirmação de e-mail e políticas do piloto. [Regra e evidências](docs/registered-access-v13.md). [Cadastro, login e benefícios dos acessos](docs/account-experience-v14.md).

## O que já funciona no piloto

| Área | Implementação | Acesso |
| --- | --- | --- |
| Conta | Cadastro, confirmação local de e-mail, login/logout, recuperação, exportação e controles de exclusão | `/conta`, `/estudar` |
| Prática | Sessões persistentes, retomada, idempotência, cota Free de 30 questões/mês e comentários por alternativa após responder | `/estudar` |
| Diagnóstico | Cinco itens introdutórios das quatro áreas e primeira recomendação; não prevê nota | `/diagnostico` |
| Planejamento | Sessões de 15/30/60 minutos, revisão espaçada, erros e favoritos para acesso pago de teste | `/painel`, `/caderno` |
| Simulados | Seis questões por treino; primeiro dia com redação em 30 min, segundo dia em 15 min; prazo e cota no servidor | `/simulados` |
| Conteúdo | 20 questões de Matemática do ENEM 2025 com proveniência; seis trilhas/18 lições introdutórias, após login | `/estudar`, `/biblioteca` |
| Acervo | PDFs históricos após login, separados dos itens interativos; fonte oficial quando a cópia local não está instalada | `/acervo-enem` |
| Oficina | Texto, notas fixas ilustrativas, marcações e reescritas persistentes por conta; sem OpenAI | `/redacoes` |
| Carteira | Lotes sandbox com vencimento, reserva, consumo, liberação, revogação e histórico; integração à oficina demonstrativa | `/carteira` |
| Pedidos | Contratos/snapshots, pagamento consultado no servidor, concessão única, holds de cupom, cancelamento local e tratamento de estornos em sandbox | `/planos` |
| Operação | Triagem local somente leitura de pedidos em análise; sem aprovação, concessão ou estorno automático | `python -m backend.moirae.order_review` |

Os simulados são treinos reduzidos, não provas oficiais completas. As lições autorais estão em revisão editorial; o conteúdo não equivale ao catálogo integral de um cursinho. Acesso pago de teste não representa compra real.

## Planos e créditos

O catálogo mensal atual, versão 3, preserva o acréscimo único de 10% aprovado para os preços. Pedidos antigos mantêm seus contratos e snapshots.

| Plano proposto | Preço do produto | Período | Correções de redação previstas |
| --- | --- | --- | --- |
| Free | R$ 0 | Cota renovada a cada mês | Não inclui |
| Essencial | R$ 44 | 30 dias, renovação manual | 10 por ciclo |
| Avançado | R$ 110 | 30 dias, renovação manual | 30 por ciclo |

A correção real ainda não está liberada. A oficina usa notas fixas e créditos de demonstração separados dos créditos reais. Recursos pagos e quantidades acima definem o contrato proposto; não constituem oferta de serviço já disponível para venda.

Pacotes de 5/10/30 créditos têm preços de produto de R$ 27,50/R$ 49,50/R$ 132,00. O ciclo interno sandbox de pedidos e lotes está implementado; checkout dos pacotes exige configuração explícita de provedor, carteira e validade. **Validade de 90 dias permanece proposta**, sem padrão comercial aprovado. Parcelamentos longos continuam simulações; o checkout integrado atual é **1x**. Não somar juros estimados ao valor de um pedido validado como pagamento único.

### Cupom aprovado

- 5% de desconto exclusivamente no Avançado.
- Chance independente de 1 em 100 por giro; demais 99 ficam sem prêmio e sem código resgatável.
- Três meses de calendário desde o giro vencedor, no fuso de Brasília, com ajuste para o último dia do mês quando necessário.
- Uma participação por conta/campanha, uso único e sem acúmulo.
- O fim da participação não encurta a validade já emitida.

A política é versionada e testada. **Nenhuma campanha operacional foi criada:** datas e limite global ainda dependem de definição. Sem campanha configurada, a roleta é demonstrativa. [Política detalhada](docs/coupon-policy-v8.md).

## Acompanhar a validação pelo GitHub

No PC do trabalho, você pode ler os resultados da CI e organizar a conferência manual pelo navegador, sem instalar ou executar ferramentas. Consulte o [pacote de validação](docs/validation-package.md), com checklist e formulário de problemas. O pacote não executa QA visual nem ativa serviços comerciais.

## Executar no Windows — PowerShell, sem WSL

Requer Python instalado no Windows (CI em 3.12; validação local anterior também em 3.13) e Node.js para os testes web (CI em 24). Use uma pasta do usuário, fora de `C:\Windows\System32`.

Se ainda não tiver uma cópia, clone `main`. Se já tiver, preserve alterações locais e bancos antes de atualizar; não clone novamente dentro do projeto existente.

```powershell
git clone --branch main https://github.com/Sarhuman/MOIRAE-CONCURSOS.git MOIRAE-CODEX
Set-Location MOIRAE-CODEX
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements-dev.lock
```

Na mesma janela PowerShell, configure o piloto local. O arquivo `.env.example` é referência e **não é carregado automaticamente**.

```powershell
$env:MOIRAE_ORIGIN='http://127.0.0.1:8000'
$env:MOIRAE_SECURE_COOKIE='false'
$env:MOIRAE_DB=Join-Path $PWD 'var\henrique-main.sqlite3'
$env:MOIRAE_ESSAY_DEMO='true'
$env:MOIRAE_COMMERCE_SANDBOX='false'
$env:MOIRAE_MP_SANDBOX='false'
$env:MOIRAE_ESSAY_AI='false'
$env:MOIRAE_ESSAY_AI_REVIEWED='false'
```

**Somente para criar um banco novo:** o preparador pede uma senha de teste, cria a conta `henrique@example.test` já verificada e concede acesso local Avançado. Não envia e-mail, não cobra e não chama OpenAI. Recusa sobrescrever qualquer arquivo existente.

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.local_playtest --database "$env:MOIRAE_DB" --email henrique@example.test
```

Para iniciar ou retomar o servidor com esse banco:

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.preflight
.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Abra **http://127.0.0.1:8000/estudar**. Use sempre a mesma origem, inclusive nos links de confirmação. Cadastros feitos pela interface precisam do link privado gravado em `mail-outbox`, ao lado do banco; a conta criada pelo preparador já vem verificada. Não exponha tokens ou o banco pelo servidor estático.

Para testar a carteira com três créditos em **outro banco novo**, siga [o roteiro da carteira](docs/wallet-essay-flow-v7.md). O [roteiro de validação Windows](docs/windows-wallet-validation-v9.md) e [o ciclo financeiro atual](docs/sandbox-orders-v10.md) detalham os percursos. O servidor acima aceita somente acesso no computador local; celular físico exige configuração própria.

## Testes

Na raiz do projeto, em PowerShell:

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q
node --test (Get-ChildItem tests\*.test.cjs | ForEach-Object FullName)
.\.venv-win\Scripts\python.exe -m compileall -q backend
```

A consolidação inicial foi validada com **245 testes Python e 16 JavaScript**, com CI em Windows/Ubuntu e frontend. Para a contagem do HEAD atual, consulte os resultados e resumos da CI; novos testes podem ampliar a suíte. As execuções dos mesmos testes em plataformas diferentes não são somadas. O aviso conhecido TestClient/HTTPX continua documentado, sem supressão pelo lockfile.

**Validação visual parcial realizada em 05/11/2026:** navegador integrado com backend real e banco sintético, cinco questões no desktop/360 px, recarga/reinício, carteira/oficina e medidas em desktop/360/390/430 px. [Evidências e limites atuais](docs/review-continuation-v12.md). Celular físico, zoom 200%, movimento reduzido e auditoria completa de acessibilidade continuam pendentes. TestClient e fixtures não substituem essas verificações.

## Arquitetura e limites

- Monólito modular: identidade, prática, desempenho, redações e billing, com adaptadores separados dos provedores externos.
- Cookies de sessão, origem/CSRF, titularidade, cotas, preços e idempotência conferidos no servidor.
- SQLite/WAL para piloto de **instância única**; contratos e migrações aditivos até schema 15. Não executar múltiplos hosts sobre o arquivo nem alegar operação distribuída.
- Ledger e worker de correção real separados da oficina e dos créditos sandbox; nenhum novo worker/ledger paralelo.
- Confirmação financeira exige consulta ao provedor; retorno de checkout não concede crédito. Reembolso parcial ou consumo exige análise monetária.
- Não há endpoint público de concessão ou aprovação administrativa. A [triagem operacional](docs/order-review-v11.md) abre o banco somente para leitura.
- Bancos, credenciais, tokens de e-mail, PDFs privados e relatórios operacionais ficam fora do Git. O repositório não configura produção automaticamente.

## O que falta antes de vender

1. Validação visual real dos fluxos em desktop/celular e acessibilidade.
2. Homologação externa Mercado Pago com contas de teste, webhook e conferência das tarifas/condições efetivas.
3. Validade/termos dos pacotes, datas/limite da campanha e política monetária para créditos consumidos/devolução parcial.
4. Operação autorizada e auditável para resolver casos em análise; a triagem atual não resolve pedidos.
5. Avaliação pedagógica, modelo, custos, privacidade e operação da correção real; **não habilitar OpenAI nesta etapa**.
6. Entrega real de e-mail, atendimento, retenção/exclusão, revisão editorial e infraestrutura persistente com backup/restauração.

## Documentação

Comece pelo [índice da documentação](docs/README.md) e por [DEVELOPMENT.md](DEVELOPMENT.md). O [registro da consolidação](docs/main-consolidation.md) identifica o histórico integrado à `main` e as limitações preservadas. [Changelog](CHANGELOG.md).
