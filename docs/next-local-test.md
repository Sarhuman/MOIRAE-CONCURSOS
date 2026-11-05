# Próximo passo: testar no Windows nativo (PowerShell)

Execute na pasta do projeto no PowerShell, preferencialmente dentro da sua pasta de usuário, fora de System32. O Python precisa estar instalado no Windows; a venv do Linux não é reutilizável.

Use um checkout separado e atualizado da `main` para evitar misturar alterações suas. Este roteiro executa apenas o piloto local, sem publicação.

```powershell
git clone --branch main https://github.com/Sarhuman/MOIRAE-CONCURSOS.git MOIRAE-PLAYTEST
cd MOIRAE-PLAYTEST
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements-dev.lock
$env:MOIRAE_ORIGIN="http://127.0.0.1:8000"
$env:MOIRAE_SECURE_COOKIE="false"
$env:MOIRAE_DB=Join-Path $PWD "var\henrique-playtest.sqlite3"
$env:MOIRAE_ESSAY_DEMO="true"
$env:MOIRAE_ESSAY_AI="false"
$env:MOIRAE_ESSAY_AI_REVIEWED="false"
$env:MOIRAE_MP_SANDBOX="false"
.\.venv-win\Scripts\python.exe -m backend.moirae.local_playtest --database "$env:MOIRAE_DB" --email henrique@example.test
.\.venv-win\Scripts\python.exe -m backend.moirae.preflight
.\.venv-win\Scripts\python.exe -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

O comando pede uma senha de teste duas vezes, sem mostrá-la. Não use sua senha pessoal. E-mail de teste: henrique@example.test. A conta já vem verificada, com plano Avançado local e 30 créditos demonstrativos por concessão. Não envia e-mail, não inicia pagamento e não configura OpenAI. O histórico financeiro identifica local_test. A criação só aceita banco novo: se existir, mantenha-o e escolha outro nome para repetir o preparo. Não tente rodar esse comando em produção.

O preflight só lê a configuração; mostra presença de chave como booleano e nunca o valor. Não verifica credenciais na rede. A conta e o banco gerados são descartáveis; concessão local não é uma compra. Recursos de correção real continuam indisponíveis com as travas false.

## O que testar

1. Abra http://127.0.0.1:8000/estudar e entre com o e-mail acima e a senha escolhida.
2. Abra /painel, escolha 15 minutos e inicie. Responda pelo menos uma questão errada e termine a sessão.
3. Abra /caderno: confirme o erro, marque favorito e recarregue. A resolução deve abrir sem nova tentativa.
4. Volte a /painel: confira a próxima data de revisão. A revisão só vence após o intervalo; não ajuste o banco manualmente para simular sucesso.
5. Abra /redacoes: envie texto de teste e gere o resultado demonstrativo. As notas fixas devem estar identificadas; isso não avalia a redação.
6. Abra /redacoes-ia: a correção real deve informar que está desativada, sem reservar crédito.
7. No celular, se for testar pela rede local, será necessária configuração própria de origem e acesso; o servidor acima aceita somente o computador local. Para primeira revisão móvel, use o modo responsivo do navegador e registre que é emulação.

Confira também contraste, foco por teclado, texto em 200% e larguras de 360/390/768/1440 pixels. Relate URL, ação realizada, resultado esperado e o que apareceu. Não envie senha, chave ou banco com dados pessoais.

## Próxima etapa da correção real

Prepare redações com autorização de uso e notas humanas por competência, preferencialmente com divergências resolvidas por revisão. O arquivo privado para comparação offline deve ser uma lista JSON com os campos abaixo; não comite textos de alunos ou dados pessoais.

- id: identificador pseudônimo único.
- human_reviewed: true; authorized_use: true (declarações de quem prepara o corpus, não verificações automáticas).
- model, rubric_version, prompt_version: versões exatas.
- human_scores e predicted_scores: objetos com chaves "1", "2", "3", "4", "5" e notas inteiras 0/40/80/120/160/200.

Execute `.\.venv-win\Scripts\python.exe -m backend.moirae.essay_benchmark /caminho/privado/corpus.json` para imprimir métricas sem fazer chamadas externas. O comparador rejeita corpus vazio, IDs repetidos e dados sem declarações de revisão/autorização. Compara erro absoluto médio e concordância por competência, separando versões. Não avalia comentários nem decide aprovação; a saída permanece approved=false. Referências humanas sintéticas dos testes não constituem corpus validado.

Só depois: definir modelo, limites de custo, privacidade e avaliação pedagógica, configurar credencial exclusivamente no worker e fazer um ensaio externo controlado. Não envie a chave pelo chat. As travas de correção real continuam false neste roteiro.

## Windows / PowerShell

Use Python 3.13 e uma pasta gravável em Documents, fora de System32. Cada janela tem suas próprias variáveis; o script abaixo as define juntas e usa caminho absoluto para o banco.

```powershell
py -3.13 -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install -r requirements-dev.lock
powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

O script pede uma senha somente para criar um banco novo. Banco existente é preservado. Para selecionar uma cópia preservada: `powershell -ExecutionPolicy Bypass -File .\scripts\start-local.ps1 -Database 'C:\caminho\banco.sqlite3'`. Não copie um SQLite enquanto o servidor estiver rodando. Preserve também arquivos WAL/SHM, se presentes, e a pasta mail-outbox; recrie o venv no destino.

Cadastro pela interface requer confirmação: em Minha conta, solicite novo e-mail; abra localmente o JSON mais recente em `mail-outbox`, ao lado do banco indicado no terminal. O link é privado, não o cole em relatórios. Links antigos expiram ou são substituídos. Use sempre 127.0.0.1:8000, inclusive ao abrir o link. A conta criada por local_playtest já é verificada; sua concessão vence após 30 dias. O script não altera confirmação, termos ou concessões de contas existentes.

Diagnóstico sem alterar dados (execute na pasta do projeto):

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.local_diagnose --database 'C:\Windows\System32\MOIRAE-PLAYTEST\MOIRAE-PLAYTEST\var\henrique-windows.sqlite3'
```

`local_test` no pedido identifica preparo administrativo; cadastro pela interface não cria esse pedido. Verificação isolada não prova como a conta foi criada. Se houver acesso negado em System32, execute o diagnóstico na janela que originalmente criou o banco e preserve uma cópia completa antes de mudar de pasta. Não altere ACLs recursivamente nem substitua o banco.
