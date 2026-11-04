# Importação do ENEM — primeira edição preparada: 2025 regular, cadernos azuis

## Estado real

Importador offline implementado e testado com PDFs sintéticos autorais. Os links dos quatro PDFs foram conferidos no HTML da página oficial do Inep. Em 03/11/2026, o ambiente conseguiu consultar a página, mas recebeu HTTP 503 nos quatro downloads. Não houve extração nem importação de questões oficiais reais. O catálogo do aluno continua com as 12 questões autorais introdutórias do MVP.

Manifesto: data/inep/enem-2025-regular-blue.json. A edição regular foi escolhida explicitamente; aplicações regionais e reaplicações ficam fora deste lote. O manifesto não mistura cadernos de outras cores ou aplicações.

## Executar

Na raiz do repositório, instalar requirements-dev.lock. O pypdf é uma dependência apenas da ferramenta de conteúdo, não do servidor de prática.

```sh
.venv/bin/python -m backend.moirae.importing.inep \
  --manifest data/inep/enem-2025-regular-blue.json \
  --input-dir var/inep/2025/originals \
  --output-dir var/inep/2025/review-001 \
  --download
```

Se o servidor do Inep não responder, baixe os mesmos quatro PDFs pelo portal oficial, salve-os com os nomes originais em var/inep/2025/originals e repita sem --download. Não renomeie uma prova de outro caderno para fazê-la corresponder ao manifesto.

Saídas: candidates.json com rascunhos e report.json com procedência, hashes, totais, lacunas e ambiguidades. A saída não pode existir: outro processamento usa novo diretório para preservar revisão anterior. O hash do lote permite reconhecer a mesma versão das fontes. Arquivos originais alterados não são sobrescritos pelo downloader; para uma retificação, use novo diretório.

As pastas de originais e extração estão ignoradas pelo Git. Preserve-as em armazenamento controlado com backup; o repositório registra a receita e os metadados, não redistribui PDFs ou textos de terceiros. O downloader não publica nem determina autorização de uso comercial.

## O que a ferramenta faz

- Só aceita HTTPS no domínio download.inep.gov.br e diretório oficial, sem redirecionamentos. Valida correspondência entre nome, ano, dia e caderno.
- Limita PDF a 40 MiB, exige assinatura PDF e limita quantidade de páginas antes de extrair texto.
- Calcula SHA-256 de cada original e registra URL, tamanho e versão do lote.
- Extrai texto com pypdf, preservando bloco bruto e referências de páginas. Não inventa alternativas, descrições de imagens ou resoluções.
- Separa candidatos por título de questão e informa numerações ausentes e contagens esperadas.
- Preserva ocorrências de questões 1–5 em língua estrangeira separadamente, com idioma pendente de revisão. Não presume qual é inglês ou espanhol pela ordem do PDF.
- Extrai candidatos ao gabarito e só vincula quando a correspondência é inequívoca. Duplicatas e faltas ficam pendentes. Marca anulação/exclusão quando o texto contém essa informação.
- Mantém todos os registros em draft, com revisão editorial e de direitos falsas. Não há endpoint nem comando de publicação nesta entrega.
- Não modifica a base de contas, tentativas ou cotas do MVP e não disponibiliza rascunhos aos alunos.

## Conferência obrigatória antes de usar no produto

A extração por texto não garante a ordem das colunas, completude de fórmulas, imagens, gráficos, tabelas ou passagens compartilhadas. Não houve validação deste extrator no layout real dos PDFs de 2025 devido à indisponibilidade. As contagens são alertas, não certificação de integridade.

Para o primeiro dia, conferir separadamente inglês e espanhol. A expectativa de extração inclui os dois conjuntos de questões de língua estrangeira, enquanto cada aluno responde apenas um conjunto. Conferir gabarito do dia/caderno/aplicação e eventuais retificações na fonte antes de aprovar qualquer item. Nenhum ponto ambíguo é resolvido por palpite do importador.

Etapas posteriores: revisar enunciado e cinco alternativas; restaurar/recortar recursos visuais com páginas e coordenadas; conferir gabarito; escolher idioma; classificar assunto/habilidade; produzir e revisar explicação própria; documentar a condição de uso do material. Só então construir o fluxo de aprovação/publicação. Uma questão anulada não deve ser usada como item pontuado.

Deduplicação entre cores ainda não foi implementada. O lote trabalha com uma cor por dia para evitar inserir as mesmas provas por cores diferentes. O identificador do candidato conserva caderno, número e ocorrência; ele não prova que duas questões em outras edições são pedagogicamente idênticas.

## Testes

```sh
.venv/bin/python -m pytest -q tests/test_inep_import.py
```

Os testes cobrem extração de PDF sintético, gabarito, anulações, repetição de número em idiomas, hashes estáveis, ausência de arquivos, PDF falso, URLs proibidas, correspondência do manifesto e falha de download sem criar saída inválida. Não fazem chamadas ao Inep e não precisam de OpenAI.

## Acervo baixado em 03/11/2026

Foram recuperados 98 PDFs oficiais vinculados às páginas de 1998–2025: 290.064.379 bytes e 2.013 páginas. O índice `data/inep/archive-index.json` registra URL, nome, tamanho e SHA-256. Os arquivos ficam em `var/inep/archive/<ano>/`, fora do Git. Há materiais suplementares com nomes de aplicações distintas: nunca combine automaticamente seus gabaritos com outro caderno.

A página `/acervo-enem`, acessível pelo painel e pela área de estudo, permite filtrar o ano e baixar a cópia local. Em outra instalação é preciso executar `.venv-win\Scripts\python.exe -m backend.moirae.importing.archive`; sem os PDFs locais, use a fonte oficial indicada na página. O download usa curl.exe com validação HTTPS nativa do Windows, sem desativar certificados.

Extração inicial: 2020–2025, 185 candidatos por edição (incluindo ocorrências distintas das questões de língua estrangeira), total 1.110. `data/inep/extraction-summary.json` registra os totais; textos e relatórios completos ficam em `var/inep/review-archive/`, com 2025 corrigido em `2025-v2`. Os lotes anteriores foram preservados. Nenhum desses candidatos foi publicado no catálogo interativo: extração em PDF não comprova separação das alternativas, imagens, interpretação do gabarito, resolução ou classificação pedagógica. Edições anteriores a 2020 estão disponíveis em PDF; a adaptação dos formatos antigos ainda está pendente.
