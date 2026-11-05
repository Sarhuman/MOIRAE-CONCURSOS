# Página pública — campanha visual v3

## Entrega

Paleta editorial: cobalto #2849df, coral #ff795b, menta #b8edd7, creme #fff7ec e texto azul-marinho #17243b. A folha campaign-v3.css é carregada somente pela página pública e todos os seletores são limitados a .public-page. O styles.css compartilhado e as telas autenticadas não foram modificados nesta revisão.

Abertura com ilustração de estudantes, chamada e ações preservadas. O cartão interativo 15/30/60 foi movido para uma seção própria, sem mudar IDs e handlers. Segunda arte na chamada da oficina de escrita. Planos, questão e reescrita continuam com os contratos anteriores. Sem alteração de preços, permissões, cobrança ou publicação.

## Artes

| Arquivo | Dimensões | Bytes |
|---|---|---|
| web/art/study-hero-v1.webp | 1448 × 1086 | 274374 |
| web/art/writing-workshop-v1.webp | 1254 × 1254 | 213970 |

Geração pela ferramenta integrada ImageGen, seguida apenas de conversão de formato para WebP. As artes não contêm números ou textos gerados; são ilustrações de marca, não depoimentos ou resultados de alunos. Originais PNG preservados no ambiente de geração. As versões WebP são os arquivos consumidos pelo projeto, sem dependência de URLs externas. Hero com prioridade alta; segunda imagem com lazy loading. Dimensões explícitas e texto alternativo nas duas imagens.

### Prompt da abertura

Use case: ads-marketing. Asset type: hero illustration integrated into MOIRAE Brazilian ENEM study website, not a full webpage or mockup. Create a striking premium editorial illustration, landscape 4:3 composition. Two Brazilian young adult students (clearly 18+), a Black woman with curly dark hair and a brown-skinned man with short dark hair, collaboratively studying with an open notebook, pencil and small laptop. Warm, optimistic, lively expressions, smart contemporary streetwear, tasteful oversized shapes, art-directed cut-paper collage mixed with painterly dimensional shading and subtle risograph texture. Around them a few large floating open books, coral pencil, little mint shapes and four-point stars, suggesting curiosity and progress rather than graduation. Cohesive palette cobalt blue #2849df, deep navy #17243b, coral orange #ff795b, mint #b8edd7, cream #fff7ec. Cream background with playful cobalt organic backdrop and coral sun-like disk. Subjects and objects centered, generous safe margin, crisp silhouettes that read well at mobile size. Refined professional edtech art direction, human and memorable, absolutely no words, letters, numbers, logos, text, UI cards, charts, badges, watermarks, no graduation caps, no photorealism. The entire composition should be finished artwork, no borders.

### Prompt da escrita

Use case: ads-marketing. Asset type: supporting editorial illustration for MOIRAE Brazilian ENEM writing workshop. Create a square premium cut-paper collage illustration with subtle painterly shading and risograph grain. A large flowing sheet of cream paper curls upward like a wave, a coral-orange pencil sweeps diagonally across it, an open cobalt blue book at the bottom, small mint-green folded paper shapes and a single cobalt four-point star. Art communicates the joy of writing, revision and creativity. Cohesive palette strictly cobalt #2849df, coral #ff795b, mint #b8edd7, dark navy #17243b and warm cream #fff7ec. Background warm cream, generously padded composition. No text, no letters, no numbers, no diagrams, no charts, no interface, no border, no watermark.

## Verificação

Chromium headless executado localmente: larguras 360/390/768/1440 sem rolagem horizontal involuntária; hero carregado; seletor 15 min; resposta correta da questão; comparação de reescrita; nenhuma exceção JavaScript. Zoom de layout 200% por CSS em viewport 1440 verificado; o pequeno excesso de largura dos planos foi corrigido com grid de largura mínima zero e empilhamento até 900 px. Essa emulação não substitui o zoom nativo ou teste em celular físico.

Capturas desktop e móvel inspecionadas na abertura. Validação de HTML (IDs únicos e referências às imagens), parsing de CSS e seis testes Node existentes da oficina aprovados. Sintaxe de app.js validada. Não é auditoria completa de acessibilidade nem validação de todos os fluxos autenticados. Sem novas chamadas de IA pelo aplicativo.
