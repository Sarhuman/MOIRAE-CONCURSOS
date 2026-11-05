# Acessibilidade v15 — revisão por código e testes

Rodada do PR #10 após `cbd56bb`, Windows nativo. Nenhum navegador foi automatizado nesta rodada. A tentativa anterior com Firefox foi interrompida pela proteção da plataforma; não houve contorno.

## Problemas corrigidos

- Prática: trocar de questão apenas rolava a tela e podia deixar o foco no botão anterior. Iniciar/trocar agora foca a legenda da questão, com `tabindex=-1`, sem adicionar paradas na sequência Tab.
- Entrar/sair e confirmação pendente ocultavam o controle acionado sem destino de foco definido. Ações explícitas agora focam a orientação, questão, resultado ou e-mail conforme o estado. A restauração automática inicial não rouba foco.
- Retomada explícita de atividade concluída foca a região nomeada do resultado; não reinicia a atividade.
- Mensagens de ações em Minha conta recebem foco, inclusive quando o formulário acionado é ocultado.
- Diálogos de planos, simulado e pacote sandbox recebem nomes explícitos ligados ao título. Confirmações que iniciam consumo de cota/tempo, encerram simulado ou abrem checkout de pacote começam em Voltar/Continuar escrevendo. Permanecem diálogos nativos, sem armadilha de teclado própria.
- Destinos existentes de “Pular para o conteúdo” passam a ser programaticamente focáveis. Select/textarea recebem indicação global de foco; cabeçalhos, navegação e controles podem quebrar linha, com proteção para textos longos.
- A preferência de movimento reduzido já desativava parte das transições. Agora a proteção global cobre animações/transições/rolagem suave também em pseudoelementos. A roleta reduzida publica o resultado imediatamente, sem rotação e sem temporizador de animação. O caminho normal mantém sua animação; regras/cupom/resultado do servidor não foram alterados.

## Evidências executadas

- **23 testes JavaScript aprovados**, incluindo quatro casos novos de foco do controlador da prática, um da conta/recuperação e dois de movimento normal/reduzido da roleta.
- **3 testes Python estruturais aprovados**: nomes e referências dos diálogos/foco inicial seguro; links de pulo e destino; IDs únicos e ausência de tabindex positivo em todos os HTML locais.
- Sintaxe de todos os JavaScript e `git diff --check` aprovados.
- Testes de foco usam DOM mínimo em VM e respostas sintéticas. Eles verificam a lógica executada, sem provar comportamento nativo de Tab, leitura de tela, CSS aplicado ou suporte de um navegador real.
- A CI completa do commit é informada na descrição do PR. Contagens locais selecionadas e plataformas não devem ser somadas como testes distintos.

## Validações manuais pendentes

**Zoom real de 200% e movimento reduzido no navegador/SO continuam pendentes.** As alterações de CSS e os testes de preferência sintética não encerram essas verificações. Também permanecem pendentes o percurso completo com teclado após estas mudanças, leitor de tela/contraste, celular físico e aceite final de cadastro na UI. Não foram produzidas novas capturas; as imagens v14 pertencem à revisão anterior.

## Roteiro Windows

1. Na raiz da cópia atualizada, inicie o servidor com `.\scripts\start-local.ps1` e seu banco isolado conforme README; use dados sintéticos, sem integrações externas.
2. Com Tab/Shift+Tab e Enter/Espaço, confira pulo de navegação, modos de entrada, erro de login, confirmação pendente, login Free/pago e saída. O foco deve permanecer visível e acompanhar cada mudança explícita.
3. Inicie uma atividade, responda, avance e conclua. Confira foco da próxima questão/feedback, recarga sem reiniciar e retomada do resultado. Em diálogos, confira título anunciado, foco inicial, Tab/Shift+Tab, Escape e retorno ao acionador. Não confirme compras.
4. Ative zoom de navegador em 200%, verificando o indicador real. Confira cadastro, conta, painel, planos e diálogos em janela desktop e estreita: sem cortes de texto/controles ou perda de função. Restaure o zoom depois.
5. Ative temporariamente reduzir animações nas preferências do SO/navegador. Confira rolagem instantânea, ausência de transições/rotação e resultado imediato da roleta **demonstrativa**; restaure a preferência depois. Não execute giro com prêmio nem checkout.

PR em draft, sem merge/deploy, cobrança real ou OpenAI. Bancos/checkouts anteriores preservados; decisões comerciais e homologação financeira continuam pendentes.
