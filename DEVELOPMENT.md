# Desenvolvimento da página pública

## Executar

Requer Python 3 apenas para servir os arquivos, sem dependências de aplicação:

```sh
python3 -m http.server 8080 --directory web
```

Abra http://localhost:8080. A pasta `web` contém somente HTML, CSS e JavaScript estáticos. Nenhum serviço externo, rastreador, fonte remota ou segredo é necessário.

## Limites desta entrega

A questão é autoral e demonstrativa, com correção no navegador. Não há cadastro, armazenamento de respostas, enforcement de cotas, dashboard, pagamento ou correção de redação. O gabarito local é adequado somente à demonstração; questões reais devem ter resposta validada no servidor conforme o README.

Os planos são propostas sem preços ou checkout. Os links de disponibilidade levam à explicação do estado do produto, sem captar dados pessoais.

## Validação

Executar `node --check web/app.js` para sintaxe. Conferir no navegador em 360, 768 e 1440 pixels: navegação, ausência de rolagem horizontal, teclado, respostas certas/erradas, tentativa vazia, reset e abertura das dúvidas. Testar zoom de 200% e preferência por movimento reduzido.

## Próxima etapa

Definir stack e contratos da API antes de adicionar autenticação e prática com cotas. Manter a página pública independente de dependências da área autenticada. Não liberar recursos premium por flags no navegador.

## Atualização: oficina e sessões demonstrativas

A identidade usa azul-escuro e verde-lima. Seletor de 15/30/60 minutos muda apenas exemplos fixos. A oficina inclui três marcações, comentários orientadores, rascunhos separados em memória e comparação textual segura. Não representa uma chamada à OpenAI.

Verificação adicional: selecionar as três durações; trocar C3/C4/C5; comparar reescrita; voltar ao comentário e conferir preservação; limpar; recarregar e conferir descarte. Texto HTML digitado deve aparecer literalmente. Espaços sozinhos não são uma reescrita válida.

A integração OpenAI é futura e está especificada em docs/essay-workshop.md. Nenhuma variável de chave é necessária para executar esta demonstração.

Fixtures: web/essay-fixture.js é compartilhado entre demonstração e testes. Execute `node --test tests/essay-fixture.test.cjs` na raiz do repositório. Os testes não acessam a OpenAI.
