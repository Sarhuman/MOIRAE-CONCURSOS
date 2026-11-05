# Consolidação do piloto na main

A solicitação do Henrique de atualizar a `main` autoriza integrar o código e sua documentação. Isso substitui a instrução anterior de manter os PRs apenas em draft para esta consolidação; não ativa produção, pagamentos reais ou OpenAI.

## Estratégia

O trabalho foi desenvolvido em uma cadeia de branches/PRs, enquanto `main` mantinha somente o README inicial (`3c977c9`). Antes de consolidar, foi verificado que os HEADs dos PRs #1–#7 são ancestrais do HEAD `6d8bcf4` do PR #8 e que a `main` também é ancestral. Portanto, o PR #8 pode ser direcionado à `main` para integrar a árvore completa em um único merge, preservando o histórico e evitando versões intermediárias antigas no ramo principal.

| PR | Entrega histórica |
| --- | --- |
| #1 | Base documental ENEM |
| #2 | Página pública e oficina aberta |
| #3 | Conta/prática Free persistente |
| #4 | Importador INEP |
| #5 | Cota mensal e simulados |
| #6 | Contas verificadas e privacidade |
| #7 | Billing e acesso sandbox |
| #8 | Oficina persistente, conteúdo, carteira, cupons, pedidos e triagem |

Após confirmar a integração, PRs anteriores ainda abertos e sem alterações exclusivas podem ser encerrados como incorporados pela consolidação; as branches são preservadas. Não usar force-push, sobrescrever checkouts locais ou apagar bancos para sincronizar.

## Documentação de entrada

README e DEVELOPMENT foram reescritos para refletir o piloto real e Windows nativo; `docs/README.md` identifica fontes atuais e histórico. `.gitignore` passa a proteger `.venv-win`, variantes de `.env`, saídas locais e bancos SQLite adicionais. `.env.example` permanece versionado. Não foi alterada a lógica da aplicação nem a versão 15 do schema nesta consolidação documental.

## Evidência e limites

A base de código `6d8bcf4` passou em 245 testes Python e 16 Node, com CI Windows, Ubuntu e frontend aprovada (execução 41957986384). O commit documental da consolidação será submetido à CI e o resultado final deve ser consultado no PR/checks. Não somar os mesmos testes entre sistemas.

Foi conferido no GitHub que Pages está desativado e que o único workflow versionado é de testes, sem passos de deploy. Nenhuma configuração de publicação ou serviço externo foi habilitada por esta rodada.

Permanecem as pendências registradas no README: conferência visual real, homologação financeira externa, validade/termos dos pacotes, datas/capacidade da campanha, reembolso monetário de créditos consumidos, resolução operacional autorizada e avaliação pedagógica/privacidade/custos da correção real. Fixtures e testes automatizados não resolvem essas dependências.

## Atualizar uma cópia local com segurança

No PowerShell, primeiro confira `git status`. Em uma cópia limpa, sem trabalho local a preservar:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
```

Se houver mudanças locais, não execute reset, clean ou troca forçada. Preserve o checkout e use outra cópia/branch para atualizar. A manutenção do GitHub não modifica a cópia Windows nem seus bancos. Instale dependências com a venv do Windows; não reaproveite venv Linux.
