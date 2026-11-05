# Cadastro, login e área do aluno v14

Revisão de 05/11/2026 no PR #10, sobre a política de [acesso cadastrado v13](registered-access-v13.md). Ambiente Windows nativo, backend real em loopback e banco sintético isolado. Checkouts e bancos anteriores preservados.

## Comportamento entregue

- Entrar e Criar conta Free são modos separados. Login não solicita novo aceite. Cadastro pede aceites explícitos, desmarcados e obrigatórios, senha de 12–128 caracteres e confirmação posterior de e-mail.
- Conta pendente recebe orientação de confirmação, Minha conta e atualização do acesso. O responsável local acessa a caixa de saída privada: não há envio de e-mail pela rede nem link público na API.
- Área do aluno mostra o acesso efetivo retornado pelo servidor: cota restante no Free ou questões sem cota durante acesso pago ativo. As permissões continuam no backend.
- Free inclui 30 questões mensais compartilhadas com simulados, diagnóstico, explicações, último resultado, biblioteca introdutória e acervo autenticado. Exercícios da biblioteca continuam separados da cota de prática.
- Painel Free/visitante/pendente explica a condição e oferece um próximo passo. Controles de planejamento e dados pagos só aparecem após autorização; o Free pode continuar sem assinatura.
- Minha conta e Planos explicam os benefícios. Preços continuam vindo do catálogo: Essencial R$ 44/30 dias e Avançado R$ 110/30 dias. Créditos previstos (10/30) não anunciam correção real disponível. Checkout permanece desativado nesta validação.
- Campos de senha e aceites são limpos ao sair. Estudo, perfil e painel escondem conteúdo no pagehide e revalidam restauração do histórico. Cache dos scripts atualizados versionado.
- Cadastro em duas colunas no desktop e coluna única no celular; botões do planejamento têm espaçamento e distinção visual.

## Testes executados nesta rodada

- Windows local: `python -m pytest tests/test_accounts.py tests/test_registered_content.py -q --tb=short`: **25 aprovados em 129,89 s**. Aviso preexistente de depreciação Starlette/httpx; nenhuma asserção enfraquecida.
- `node --test tests/*.test.cjs`: **16 aprovados**. Conferência de sintaxe dos scripts e `git diff --check`.
- CI completa do novo commit: consultar o PR; os 281 testes Python da execução anterior não são apresentados como nova execução local.

## Navegação efetivamente observada

- Modos entrar/cadastro; campos obrigatórios; cadastro sem aceite bloqueado pela validação nativa. Aceites permanecem desmarcados. A submissão final do cadastro com aceite não foi realizada na UI: cadastro/confirmação foram exercitados pelos testes HTTP e fixture sintética.
- Login com senha incorreta: mensagem genérica recebe foco; senha é limpa. Login Free verificado, retomada após navegar, saldo e benefícios, painel sem controles pagos e Minha conta.
- Conta sintética pendente: login bloqueia prática; confirmação feita pela API de teste; botão atualizar acesso libera o Free sem novo login.
- Login Avançado: benefícios e painel/planejamento reais. Cinco respostas por cliques, alternando largura móvel e desktop: **4/5**. Recarga em 1366 e 360 px preserva conclusão sem voltar à primeira. Não são dois blocos independentes completos nesta rodada.
- Logout e Voltar: painel pede login, sem restaurar resultados pagos. Solicitação de recuperação retorna mensagem genérica; nenhuma senha foi alterada pela interface.
- Teclado: Espaço ativa modo cadastro; Tab segue e-mail → senha → aceite; erro de login recebe foco. Isso não substitui auditoria completa.
- Capturas reais de cadastro, login, área Free, Minha conta, planos, área e painel pagos em desktop e larguras 360/390/430 px. Sem rolagem horizontal nas medidas observadas. `metrics.json` contém as medidas persistidas após recuperação do navegador; as medidas anteriores de cadastro e Free constam no registro da ferramenta.
- Duas interrupções por tempo limite do navegador foram recuperadas pela interface suportada. Nenhuma captura foi simulada ou editada.

Seleção de imagens em [evidence/v14](evidence/v14). Originais adicionais e log local em `outputs/moirae-account-review-2026-11-05`, fora do Git. A imagem de confirmação pendente local antecede apenas a melhoria final do texto sobre onde encontrar o link; não é evidência dessa redação final.

## Pendências e roteiro Windows

Celular físico, zoom real 200%, movimento reduzido e auditoria de contraste/leitor de tela continuam pendentes. Emulação de largura não prova esses itens. Homologação Mercado Pago, lançamento do e-mail, correção real e decisões comerciais anteriores continuam pendentes.

1. No PowerShell, entre primeiro na raiz da cópia atualizada. Execute `powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1` usando um banco próprio de teste e `.venv-win` configurada conforme README.
2. Abra `/estudar?cadastro=1`; confira benefícios, campos e aceites; crie conta sintética, confirme pelo link privado da caixa de saída e atualize o acesso.
3. Entre como Free: pratique, consulte Minha conta e compare planos; painel deve oferecer continuar Free sem controles pagos. Verifique uma conta paga preparada pelo utilitário local, sem compra real.
4. Responda cinco questões, atualize e confira conclusão. Saia e use Voltar: resultados privados não devem reaparecer. Repita no desktop e celular, incluindo teclado, zoom 200% e movimento reduzido.

Sem merge, deploy, cobrança real ou OpenAI. PR permanece draft.
