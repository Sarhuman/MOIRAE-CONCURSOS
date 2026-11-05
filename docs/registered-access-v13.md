# Questões somente após cadastro — 05/11/2026

## Regra aprovada

Questões gratuitas também exigem cadastro e login. Ter assinatura não é requisito para o conteúdo Free; ter uma conta autenticada é obrigatório para Free e assinantes. O cadastro já existente registra e-mail, criação e aceite das políticas no banco, mantendo confirmação de e-mail e demais controles do piloto. Não foram acrescentados campos pessoais, consentimento de marketing, rastreadores ou envio a terceiros.

Fora da plataforma ficam a apresentação, temas das trilhas, preços/propostas e chamadas para criar conta. Dentro, o Free mantém sua cota de 30 questões de prática por mês, compartilhada com simulados; acesso pago de teste mantém questões sem cota e recursos adicionais já implementados. Não foram alterados preços, cotas ou regras financeiras.

| Recurso | Visitante | Conta Free verificada | Conta paga de teste ativa |
| --- | --- | --- | --- |
| Apresentação e comparação comercial | Sim, sem perguntas/respostas | Sim | Sim |
| Questões, diagnóstico e simulados | Login necessário | Conforme cota existente | Conforme acesso existente |
| Lições/exercícios introdutórios da biblioteca | Login necessário | Sim, sem assinatura | Sim |
| Índice do acervo e PDFs servidos pelo MOIRAE | Login necessário | Sim | Sim |
| Painel, revisão e oficina demonstrativa | Login e acesso exigidos | Restrições anteriores preservadas | Conforme plano de teste |

## Implementação

- O exercício e a reescrita interativa anônimos foram retirados da página pública. O visitante encontra chamadas para cadastro, sem enunciados, opções ou respostas embutidos. Os dados e a lógica da antiga fixture pública foram removidos dos assets.
- O conteúdo de 18 lições saiu de `web/learning-library.json` para `data/learning-library.json`, fora da raiz estática. `/api/learning-library` usa o mesmo `student` dos demais endpoints: sessão, e-mail confirmado e políticas aceitas. Não exige plano pago.
- URLs antigas do JSON e da fixture não servem conteúdo, inclusive sob `/assets`. Não basta ocultar controles no navegador; a autorização está no servidor.
- `/api/enem-archive` e `/acervo-enem/{year}/{name}` passaram a exigir o mesmo cadastro/login. A cópia PDF autorizada usa `private, no-store`; APIs usam `no-store`.
- Biblioteca e acervo exibem orientação de login ou confirmação da conta sem mostrar conteúdo em caso de 401/403. Navegação voltar/avançar revalida a sessão e limpa o conteúdo anterior.
- Progresso local das lições tem namespace opaco por conta, sem e-mail/ID bruto no localStorage. O aluno não herda marcações de outra conta no mesmo navegador. Continua sendo progresso local, sem sincronização ou novo registro de tentativas no servidor.
- A biblioteca está ligada à área autenticada de estudo. Exercícios introdutórios das lições continuam separados da cota mensal de prática, como antes; esta mudança não amplia nem reduz cotas.

O cadastro registra o usuário; não torna o repositório público ou a fonte oficial do INEP privados. A proteção descrita é dos caminhos servidos pela aplicação. Links externos já obtidos e arquivos que um usuário autorizado baixou não podem ser revogados por este controle. Nenhuma questão foi publicada nas novas capturas selecionadas abaixo.

## Evidência real

Banco novo com contas sintéticas Free e paga, API real FastAPI/SQLite e navegador integrado. Sem interceptar respostas ou simular capturas:

1. Visitante abriu a página pública: apresentação e cadastro, sem formulário de questão.
2. Visitante abriu a biblioteca: chamada de cadastro/login e zero alternativas visíveis.
3. Conta Free já cadastrada/verificada fez login: 0/30 questões usadas, acesso à biblioteca e resposta comentada de uma lição, sem assinatura.
4. Após logout e voltar no navegador, a biblioteca voltou a bloquear o conteúdo e mostrou zero alternativas.
5. Conta paga fez login: questões sem cota durante o acesso e biblioteca disponível. Seu progresso local era 0/3, sem herdar o 1/3 da conta Free.
6. Após sair, o acervo apresentou login obrigatório e nenhum link de prova.
7. Biblioteca autenticada e chamada pública foram renderizadas em 360/390/430 px: [seis medições sem overflow horizontal](evidence/v13/registered-access-metrics.json).

[Captura real: cadastro obrigatório em 390 px](evidence/v13/library-registration-required.jpg).

As capturas com perguntas após login foram mantidas apenas no diretório local de evidências; não foram acrescentadas à documentação pública. Emulação não equivale a celular físico. Os limites de zoom 200%, movimento reduzido e auditoria integral de acessibilidade registrados em v12 continuam pendentes.

## Testes

- Antes da mudança: 13 falhas e um caso já protegido, nos 14 novos cenários de acesso.
- Depois: **34 testes Python selecionados aprovados em 342,71 s**, cobrindo os novos cenários, acervo e catálogo. Incluem visitantes, Free, pago, conta não verificada, logout, cookie revogado, caminhos antigos de arquivos, isolamento do progresso e preservação dos 18 exercícios.
- Os três testes Node da demonstração pública removida foram substituídos por três verificações da nova política (sem exercícios na landing page, conteúdo fora dos assets e biblioteca pela API autenticada). Não foi mantida como requisito uma demonstração que a nova regra proíbe.
- **16 JavaScript aprovados**, sintaxe dos **18 scripts** e compilação backend/scripts aprovadas. A quantidade de scripts caiu porque a fixture pública foi retirada.
- A suíte completa passa a ter **281 casos Python**. Conferir a CI do HEAD final deste PR; não somar testes selecionados sobrepostos ou execuções Windows/Ubuntu.

## Reproduzir no Windows

1. Prepare a venv e um banco de teste conforme README. Mantenha Mercado Pago e OpenAI desativados.
2. Sem login, abra página pública, biblioteca e acervo: perguntas, respostas e links de provas não aparecem; biblioteca/acervo pedem conta.
3. Confira que `/learning-library.json`, `/assets/learning-library.json` e as antigas URLs de `essay-fixture.js` não servem conteúdo.
4. Crie/confirme uma conta Free de teste pelos fluxos existentes. Entre, confira as 30 questões e abra a biblioteca pelo link da área do aluno.
5. Responda uma lição, saia e volte: o conteúdo volta a exigir login. Em outra conta, o progresso local não deve ser herdado.
6. Repita com acesso pago de teste: login continua obrigatório, com os benefícios do plano preservados.

As correções de triagem e retomada de v12 permanecem neste PR. Sem merge, deploy, cobrança real, campanha operacional ou chamada OpenAI.
