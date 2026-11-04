# Revisão funcional e campanha visual — 04/11/2026

Base revisada: 51d84bc, PR #8 de Sarhuman/MOIRAE-CONCURSOS. Ambiente alvo: Windows nativo/PowerShell.

## Correções

- Simulado introdutório seleciona seis itens autorais, independentemente do crescimento do catálogo oficial. Mantém a duração, débito único e retomada; simulados já iniciados preservam seus itens salvos.
- Diagnósticos novos exigem cinco unidades de saldo e usam itens introdutórios das quatro áreas. Saldo insuficiente não cria sessão. Resultados, incluindo legados, mostram a quantidade observada de respostas e áreas.
- Acervo distingue a coleta histórica da disponibilidade efetiva dos PDFs nesta instalação e oferece a fonte oficial quando o arquivo não existe.
- Expectativa da migração atualizada para versão 10; teste preserva cota e atividade legadas.
- CI verifica sintaxe de todos os scripts web e executa todos os testes Node, incluindo os financeiros.

## Visual

Abertura com tipografia mais forte, destaque do conteúdo existente e seção sobre diagnóstico, resolução e revisão; preserva as artes originais existentes. FAQ corrige cadastro e preço Essencial desatualizados. Referência de estrutura comercial consultada: https://descomplica.com.br/ em 04/11/2026. A roleta da referência não foi exposta no conteúdo público recuperado; não se afirma reprodução fiel.

`coupon-demo.js` implementa somente uma experiência visual de giro em modal nativo com fechamento, retorno de foco, anúncio textual e movimento reduzido. Abre apenas por convite manual. Não emite cupom, não coleta e-mail, não faz chamadas de pagamento e não muda preços. Não há desconto comercial aprovado para ativar. Sorteio e cupom reais precisarão de backend e política comercial, sem confiar nesta animação.

## Validação

- 173 testes Python aprovados, com aviso de depreciação do TestClient/HTTPX.
- 12 testes Node aprovados, sintaxe de todos os scripts e compileall do backend aprovados.
- Navegador desktop: abertura da página, abertura/giro/conclusão/fechamento da roleta conferidos. Evidência: evidence/coupon-demo-desktop.jpg.
- Não validado em Windows real, celular físico, larguras móveis específicas ou leitor de tela. Nenhum pagamento real, merge ou deploy.

## Próximo executor

Siga codex-remaining-v5.md; não repita correções já entregues.
