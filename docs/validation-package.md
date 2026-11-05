# Pacote de validação pelo GitHub

Este pacote permite acompanhar a validação automática e organizar a conferência manual **sem instalar ferramentas nem executar comandos no PC do trabalho**. Não exige PowerShell. O código da aplicação e as regras comerciais permanecem iguais.

## Usar agora pelo navegador

1. Abra **Actions → MVP checks** para a main, ou **Checks** no PR que deseja conferir. Selecione a execução correspondente ao commit.
2. Na página da execução, leia os resumos de backend Windows, backend Ubuntu e frontend. Cada resumo registra o commit testado, contagens JUnit e resultado de compilação/sintaxe.
3. Uma suíte ausente, inválida, vazia ou com testes ignorados não recebe aprovação completa pelo resumo. Falhas anteriores não são ocultadas pela etapa de relatório.
4. Windows e Ubuntu executam a mesma suíte Python; não some seus totais como testes diferentes. Contagens antigas no README são referência da base consolidada, não resultado automático deste pacote.
5. A aba **Actions → MVP checks → Run workflow** permite disparar novamente os mesmos checks na main. Isso executa testes remotos, não abre o aplicativo, não publica site e não cria campanha.
6. Use o checklist abaixo para planejar a conferência real. No PC do trabalho, apenas acompanhe os resultados e registre decisões; deixe a execução local para o computador pessoal.
7. Ao encontrar um problema real, use **Issues → New issue → Problema encontrado na validação**; não crie uma issue fictícia. Preencha commit, ambiente, passos e esperado/observado. Não é necessário criar issues para o que não foi testado.

O resumo não copia mensagens de testes, textos, códigos de cupons ou variáveis de ambiente. Relatórios JUnit ficam no diretório temporário `var/validation` do runner, sem artefato público adicional. Os logs padrão da CI continuam no GitHub; os testes deste piloto usam dados sintéticos. Não publique relatórios operacionais reais para substituir testes.

## Checklist manual — modelo para cada execução

O registro de navegação real de 05/11/2026 está em [v12](review-continuation-v12.md), com itens comprovados e pendentes. A tabela abaixo é um modelo em branco; não copia aprovação de uma rodada para outra.

Marque cada item somente após observar a aplicação real. Preencha commit, navegador, largura, zoom e evidência. Esta lista não é uma declaração de aprovação.

| ID | Percurso | Resultado esperado | Estado |
| --- | --- | --- | --- |
| V01 | Entrar com conta sintética verificada | Login e área própria; sem dados de outra conta | Não executado |
| V02 | Diagnóstico: responder cinco questões e concluir | Quatro áreas, amostra explícita e primeira recomendação | Não executado |
| V03 | Prática: concluir, atualizar e reabrir | Conclusão preservada; não reiniciar automaticamente na primeira questão | Não executado |
| V04 | Errar uma questão, abrir caderno e marcar favorito | Erro/favorito persistem sem novo consumo de tentativa | Não executado |
| V05 | Simulado: confirmar tamanho, prazo e cota | Seis itens anunciados e débito correspondente; retomada sem novo débito | Não executado |
| V06 | Carteira com três créditos → enviar pela carteira | Disponível 2, reservado 1; texto salvo uma vez | Não executado |
| V07 | Gerar demonstração e repetir/atualizar | Reservado 0, consumido 1; disponível 2, sem consumo duplicado | Não executado |
| V08 | Abrir correção real e planos sem configuração externa | Correção real desativada; checkout indisponível; R$44/R$110, 10/30 previstos | Não executado |
| V09 | Roleta sem campanha provisionada | Apenas demonstração, sem código resgatável ou prêmio real | Não executado |
| V10 | Desktop, 360/390/430 px, zoom 200% | Sem cortes ou rolagem horizontal; conteúdo e ações acessíveis | Não executado |
| V11 | Tab/Shift+Tab, Escape, retorno de foco e movimento reduzido | Diálogos utilizáveis e animação respeitando preferência | Não executado |
| V13 | Visitante abre biblioteca/acervo; depois conta Free entra e sai | Sem perguntas antes do login; Free acessa sem assinatura; logout bloqueia novamente | Não executado |
| V12 | Carregamento, estado vazio e erro de conexão | Mensagens claras, rascunho preservado e retentativa segura | Não executado |

O preparo local no computador pessoal está em [wallet-essay-flow-v7.md](wallet-essay-flow-v7.md) e [sandbox-orders-v10.md](sandbox-orders-v10.md). Preserve bancos existentes e use banco novo para o saldo inicial de três créditos. Não habilite integrações externas para realizar esse percurso demonstrativo.

## Evidência e bloqueios

- Testes de API/domínio não substituem navegação autenticada ou acessibilidade.
- Emulação não equivale a celular físico; fixture não equivale a serviço real.
- Se a plataforma bloquear o navegador, registre a limitação e mantenha o item não executado. Não contorne a proteção nem gere capturas como se fossem reais.
- Correção OpenAI, cobrança real, homologação Mercado Pago e campanha operacional não são ativadas por este pacote.
- Validade dos pacotes, janela/capacidade da campanha e política monetária para créditos consumidos continuam dependendo de decisão.

## Implementação

O workflow existente foi estendido, sem criar uma segunda suíte ou duplicar o ciclo financeiro. Pytest e Node geram JUnit; `scripts/validation_summary.py` conta cada `testcase` uma vez, não soma contadores de suítes aninhadas e publica somente estados/contagens em `GITHUB_STEP_SUMMARY`. XML inválido ou com DTD/entidades, arquivo acima do limite e metadados inesperados não produzem aprovação falsa.

Nenhum banco de usuário é aberto pelo gerador, nenhuma credencial é coletada e nenhuma permissão adicional de escrita no repositório é concedida ao workflow. Os testes do gerador usam arquivos sintéticos temporários.

## Registro desta entrega

No executor isolado: **256 testes Python e 16 JavaScript aprovados**, com JUnit dos dois runtimes lido pelo gerador e contagens conferidas sem duplicação. Onze testes novos cobrem relatório ausente/inválido, suites aninhadas, ausência de vazamento, compilação ignorada, todos os testes ignorados, XML com entidades e limite de tamanho. O aviso TestClient/HTTPX permanece. A CI remota do novo commit deve ser consultada separadamente; nenhuma conferência visual real foi produzida por este pacote.
