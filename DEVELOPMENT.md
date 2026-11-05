# Desenvolvimento do MOIRAE web

O projeto é um piloto FastAPI/SQLite com frontend HTML/CSS/JavaScript. O caminho principal de teste é **Windows nativo, PowerShell e `.venv-win`**, sem WSL. A instalação completa está no [README](README.md#executar-no-windows--powershell-sem-wsl).

## Backend e banco

Instale `requirements-dev.lock` usando o Python da venv Windows. Execute `backend.moirae.app:create_app` com `--factory`, origem local e cookie de desenvolvimento conforme README. Use banco novo somente no primeiro preparo; não sobrescreva bancos existentes nem copie um SQLite em uso. Preserve os arquivos WAL/SHM e a caixa de saída quando aplicável.

O atalho existente `scripts/start-local.ps1` prepara apenas um banco que ainda não existe e recusa iniciar após erro de configuração. Não altera a verificação, termos ou acesso de contas já existentes. Para a carteira e integração sandbox, prefira o roteiro explícito de [wallet-essay-flow-v7.md](docs/wallet-essay-flow-v7.md).

`MOIRAE_SECURE_COOKIE=false` é exclusivo do piloto HTTP local. Pagamentos externos de teste exigem origem HTTPS e configuração privada; não remova validações para forçar homologação. `.env.example` não é carregado automaticamente. Não crie ou comite chaves reais.

## Página pública estática

Para inspecionar somente as amostras públicas, na raiz:

```powershell
.\.venv-win\Scripts\python.exe -m http.server 8080 --directory web
```

Abra http://127.0.0.1:8080. Esse servidor **não executa a API**, não fornece login, carteira ou processamento de redações e não reproduz os mounts `/assets` do FastAPI para páginas autenticadas. A roleta usa somente animação demonstrativa quando não consegue consultar a campanha. Não use a prévia estática como evidência de funcionamento do backend.

Artes originais estão em `web/art`. A biblioteca escrita e exercícios abertos são amostras, separados das tentativas/cotas do aluno. Oficinas públicas usam fixtures, sem análise de texto ou envio à OpenAI.

## Verificar mudanças

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q
node --test (Get-ChildItem tests\*.test.cjs | ForEach-Object FullName)
.\.venv-win\Scripts\python.exe -m compileall -q backend
```

A CI também verifica sintaxe de todos os scripts `web/*.js`, com backend em Windows e Ubuntu. Use testes de comportamento para cotas, créditos, autorização, concorrência, migração e integração. Provedores falsos e MockTransport não constituem homologação externa.

Para QA visual real: desktop e 360/390/430 px, Tab/Shift+Tab, Escape/retorno de foco, zoom 200%, contraste, movimento reduzido, conclusão/retomada e erros. Registre dados sintéticos, largura e modo de execução. Diferencie celular físico de emulação e fixtures de navegação autenticada. Não contorne bloqueios do navegador.

## Operação e continuidade

- Estado financeiro: [sandbox-orders-v10.md](docs/sandbox-orders-v10.md).
- Triagem sem escrita: [order-review-v11.md](docs/order-review-v11.md).
- Política do cupom: [coupon-policy-v8.md](docs/coupon-policy-v8.md).
- Correção real, bloqueada por padrão: [real-essay-evaluation.md](docs/real-essay-evaluation.md).
- Documentos históricos: consulte o [índice](docs/README.md) antes de tratar limitações antigas como pendências atuais.

Novas alterações devem partir da `main` atualizada, em branch própria, preservando o checkout antigo e alterações locais. Verifique `git status` antes de trocar de branch. Integração na `main` não equivale a deploy, ativação comercial ou autorização para chamar provedores reais.
