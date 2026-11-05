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

## Primeiro lote interativo de 2025

Quatro itens do segundo dia, caderno 7 azul, foram conferidos visualmente nas páginas 16 e 19 e contra o gabarito oficial: 136=C, 137=B, 144=D, 146=B. Não são anulados no gabarito consultado. O JSON `data/inep/enem-2025-validated.json` registra os textos transcritos, alternativas, origem, páginas e hashes. As resoluções e comentários por alternativa são do MOIRAE, não do INEP.

A questão 137 usa uma transcrição acessível dos dados do infográfico (90% dos internautas usam redes; 60% desses usuários são mulheres), identificada como tal, com a referência original. Os demais três itens selecionados não dependem de imagens. Não se publicou automaticamente texto de colunas misturadas ou questão anulada. Os demais candidatos continuam pendentes de revisão.

O botão “Praticar ENEM 2025 · 4 questões”, na área de estudo, usa as mesmas sessões, autenticação, confirmação, termos, cotas e idempotência da prática normal. Retoma a atividade em andamento em vez de duplicá-la. As quatro questões também integram o catálogo de prática; a indicação de origem distingue os itens oficiais dos exemplos autorais.

## Segundo lote interativo de 2025

Adicionados os itens 150, 151, 152 e 154, segundo dia, caderno 7 azul: gabaritos D, D, D e C. Conferência visual nas páginas 21–22 e no gabarito oficial registrado pelos mesmos hashes do lote 1. A questão 154 utiliza transcrição acessível explícita do gráfico com estoques brasileiro/estrangeiro e demanda; os demais itens deste lote não dependem de figura. As questões 149 e 153, presentes nessas páginas, continuam fora do lote: suas figuras não foram integradas.

O botão “ENEM 2025 · lote 2 · 4 questões” inicia esse bloco usando as mesmas regras de conta, cota, sessão e correção. O lote 1 permanece acessível pelo botão anterior. O catálogo tem agora oito itens oficiais de 2025 conferidos; os demais candidatos continuam pendentes.

## Terceiro lote interativo de 2025

Itens 155–159 do segundo dia, caderno 7 azul, página 23: gabaritos B, E, C, C e D conferidos no gabarito oficial. Resoluções verificadas: 20×18×16; escala 20 cm:30 m = 1:150; T/F=1,59; (14.240+120×36×1,20+10.000)/120=245,20; 20.000/250=80.

A questão 156 contém transcrição acessível explícita da figura do sol, com as duas dimensões de 20 cm. As questões 155, 157, 158 e 159 não dependem de imagem. Dados e referências de origem estão em `enem-2025-validated.json`. O botão “ENEM 2025 · lote 3 · 5 questões” preserva os dois blocos anteriores. Total integrado: 13 questões oficiais; demais candidatos continuam pendentes.

Validação no navegador: desktop 5/5 e celular emulado com um erro proposital, 4/5. Conclusão e atualização sem reinício automático em ambos. Nenhuma rolagem horizontal na largura móvel testada.

## Quarto lote interativo de 2025

Itens 162, 163, 165 e 166, segundo dia, caderno 7 azul, páginas 24–26; gabaritos B, B, D e E conferidos no gabarito oficial. A questão 162 não depende de figura. A 163 preserva, por transcrição acessível explícita, as alturas relativas das barras, o setor de futebol com metade do círculo e os 80 estudantes do basquete. A 165 preserva todos os campos preenchidos e a ausência de valores nos demais campos da tabela. A 166 preserva tempos acumulados, intervalos e distâncias do esquema.

Resoluções: reciclagem mínima de 140 t; 8 unidades gráficas=80 alunos e total de 36 unidades=360; grupo 4 com média 25 e desvio 1; tempo final de 273 s e redução de 15 s em relação ao quarto trecho. O bloco usa as mesmas regras de conta, quota, sessão e correção. Total integrado: 17 questões oficiais. Os itens 160, 161 e 164 permanecem pendentes de integração visual.

Conferência no navegador: desktop 4/4; celular emulado 3/4 com um erro proposital. Conclusão e atualização sem reinício automático; largura móvel sem rolagem horizontal.

## Quinto lote interativo de 2025

Itens 167, 168 e 169, segundo dia, caderno 7 azul, páginas 27–28; gabaritos D, E e A conferidos no gabarito oficial. A 167 apresenta transcrição acessível dos gráficos, incluindo os rendimentos a 60 km/h: 10 km/m³ para GNV e 8 km/L para gasolina. A 168 preserva todos os valores do quadro de preços. A 169 preserva a tabela das safras e transcreve, em ordem cronológica, os valores dos cinco gráficos alternativos; a adaptação é explicitamente indicada no enunciado.

Resoluções conferidas: 120/8×3−120/10×2=21; totais das autoescolas I=1.400, II=1.300 e III=1.200; produção em toneladas=área×produtividade×50/1.000. Total integrado: 20 questões oficiais, mantendo os blocos anteriores disponíveis.

Conferência por cliques: desktop 3/3; celular emulado 2/3 com um erro proposital. Atualização após conclusão sem reinício automático em ambos; sem rolagem horizontal na largura móvel testada.


## Disponibilidade por instalação — revisão de 04/11/2026

O índice versionado documenta a coleta; seu status `downloaded` não prova que o arquivo existe nesta máquina. `/api/enem-archive` calcula `available_local` na consulta, sem cache. A página oferece o PDF local somente quando disponível; caso contrário, aponta diretamente à URL oficial. O endpoint de arquivos continua limitado aos nomes do índice e não baixa URLs enviadas pelo cliente.

No PowerShell, na raiz do projeto:

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.importing.archive
```

Requer `curl.exe` do Windows e acesso ao INEP. Os PDFs ficam em `var/inep/archive`, fora do Git; preserve esse diretório entre atualizações. A coleta atualiza `data/inep/archive-index.json`; confira o resumo de falhas. Sem os PDFs, o acesso pela fonte oficial continua disponível.
