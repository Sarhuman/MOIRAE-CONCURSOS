# Oficina de redação — contrato proposto

## Implementado

Interface responsiva com exemplo autoral, seleção por competência (C3/C4/C5), orientação fixa, campo de reescrita de 20 a 1.200 caracteres e comparação antes/depois. Rascunhos distintos por marcação em memória; limpar remove o rascunho selecionado; recarregar descarta tudo. Conteúdo digitado é inserido com textContent, nunca como HTML. Não há pontuação ou avaliação semântica local.

## Integração futura com OpenAI

Não implementada neste PR. A API do produto deve autenticar o aluno, conferir propriedade do texto e direitos de acesso, reservar crédito atomicamente e enfileirar a avaliação. A chave fica no ambiente do servidor; nunca solicitar que o aluno informe uma chave e nunca embuti-la no frontend.

Contrato de domínio, independente de SDK/modelo:

- Texto e tema versionados; referência da rubrica e versão do avaliador.
- Resultado com cinco competências, nota estimada por competência, justificativas e prioridades.
- Marcações com competência, categoria, trecho literal e offsets UTF-16 no texto original (fim exclusivo), além de explicação e pergunta orientadora.
- Validar que cada intervalo reproduz o trecho literal, que a competência existe e que a estrutura e pontuações são válidas. Rejeitar marcações inconsistentes, sem inventar localizações.
- Identificar como estimativa pedagógica, sem nota oficial ou promessa de aprovação.
- Tratar texto do aluno como dado não confiável, separado das instruções. Não habilitar ferramentas ou navegação a partir da redação.
- Um identificador idempotente por envio; retries e eventos repetidos não podem consumir duas vezes. Falha técnica definitiva libera reserva. Definir como tratar envios inelegíveis antes da cobrança.
- Estados: recebido, em processamento, concluído, falhou. Não prometer resposta imediata; resposta indisponível não vira nota zero.
- Reescrita vinculada ao resultado e trecho originais, com limite de rodadas e tamanho. Nova correção completa usa novo crédito; revisão de trecho usa franquia própria.
- Limites por usuário, custo e concorrência; timeouts e teto de saída; logs sem corpo da redação ou chave. Evitar retenção desnecessária.
- Definir informação ao aluno sobre processamento externo, retenção e exclusão antes do lançamento.

## Manuscritos

Fora desta entrega. Fluxo previsto: foto, transcrição, conferência/correção pelo aluno, confirmação da versão e avaliação. Não penalizar caligrafia ou gramática com base em OCR não confirmado. Imagem e texto exigem limites de tamanho e política de retenção.

## Critérios para habilitar venda

Conjunto de redações com direito de uso e avaliação humana de referência. Comparar notas por competência, erros pedagógicos, marcações e casos ambíguos; avaliar versões novas antes de promoção. Medir custo e latência por correção e reescrita. Testar isolamento de alunos, créditos concorrentes, retries, saída malformada, tentativas de instrução no texto e indisponibilidade do provedor.

Sem GraphRAG, agentes múltiplos ou roteamento multi-provedor nesta fase. A evolução depende de problemas observados. Concursos exigirão rubricas e conteúdo próprios; não se resumem a trocar um parâmetro.

## Recomendações incorporadas para a API

- Usar Structured Outputs com JSON Schema estrito e validação local do resultado. O schema não garante correção pedagógica nem que offsets correspondam ao original; validar essas invariantes separadamente.
- Tratar recusa, resposta incompleta, timeout e falha de validação como estados próprios: não renderizar resultado parcial como correção concluída e não descontar crédito duplicado em retries.
- As fixtures autorais estão em web/essay-fixture.js, consumidas pela página e verificadas por tests/essay-fixture.test.cjs. Não precisam de chave nem rede. Na futura API, acrescentar fixtures de saída válida, recusa, resposta truncada, nota inválida e offsets incorretos.
- OCR futuro: estados aguardando imagem, transcrevendo, revisão necessária, texto confirmado e falha de leitura. Em falha, permitir nova foto ou digitação. Não iniciar avaliação nem reservar crédito de correção antes de confirmar o texto; custo de transcrição deve ter controle próprio e ser informado.

## Oficina persistente demonstrativa

O percurso autenticado `/redacoes`, separado do exemplo da landing page, agora persiste envios, resultados fixos e reescritas. Veja [essay-demo.md](essay-demo.md). Esta entrega não integra OpenAI nem avalia semanticamente o texto.

