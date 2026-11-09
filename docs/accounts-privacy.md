# Contas e privacidade — piloto local

## Entregue

- Cadastro com aceite dos termos versionados e declaração de maioridade separados do aviso de privacidade. Sem checkbox genérico de consentimento à LGPD ou marketing.
- E-mail pendente bloqueia prática e simulados. Links de confirmação duram 24 horas e são de uso único; reenvio invalida o anterior.
- Recuperação com resposta genérica, token de 30 minutos, hash no banco e revogação de todas as sessões ao trocar a senha. Não modifica a senha até a validação do token.
- Área /conta com status de e-mail, aceite para contas antigas, recuperação, exportação JSON e exclusão após reautenticação. Exportação/exclusão exigem origem e CSRF além da senha atual.
- Exportação limitada aos dados do usuário; sem hashes de senha, tokens ou chaves CSRF.
- Exclusão das tabelas de conta, sessões, respostas, redações, simulados e tokens do usuário na base ativa, além das mensagens locais. Não exclui dados de outros alunos. Não equivale a apagamento forense dos blocos de disco, WAL ou cópias externas.
- Avisos do piloto em web/privacy.html, web/cookies.html e web/terms.html. Cookies necessários documentados; analytics/publicidade não instalados, sem banner com escolhas fictícias.

## E-mails neste ambiente

No modo HTTP local, os links são gravados ao lado do banco, em var/mail-outbox, diretório 0700 e arquivos 0600, fora da pasta pública e ignorados pelo Git. Os arquivos contêm destinatário e link secreto de teste: não publicar, compartilhar, versionar ou incluir em logs.

Fluxo local: criar conta, abrir o arquivo mais recente referente à conta no servidor, copiar o link para o mesmo navegador e confirmar. A URL usa fragmento #token, removido pela tela ao abrir; o token não vai na URL da requisição HTTP. Verificação e recuperação enviam o token no corpo do POST.

Em HTTPS, o cadastro depende de um adaptador de e-mail. Para homologar com Resend, verifique o domínio no painel, configure o remetente desse domínio e mantenha o rastreamento de cliques e aberturas desativado. Configure `MOIRAE_EMAIL_PROVIDER=resend`, `MOIRAE_EMAIL_FROM`, `RESEND_API_KEY` nos segredos do backend, origem HTTPS e cookie Secure.

O envio é síncrono com timeout, sem fila. Se a entrega falhar após o cadastro, a conta fica pendente. O aluno pode entrar e solicitar outro link na área Minha conta. O Resend recebe o endereço e o conteúdo da mensagem, incluindo o link temporário. A exclusão local não remove registros do provedor. A entrega real ainda precisa ser homologada.

## Dados antigos e migração

A extensão aditiva 3 cria perfis e tokens sem remover usuários, respostas ou simulados anteriores. Uma conta antiga sem aceite/validação pode entrar e usar /conta, mas precisa aceitar os termos atuais e confirmar o e-mail para estudar. Não marcar retroativamente usuários como verificados ou termos como aceitos.

## Retenção e operação pendentes

Tokens expiram logicamente e tokens antigos são removidos na emissão de novos. As mensagens locais são excluídas ao remover a conta; durante testes, o operador deve limpar a caixa de saída ao finalizar. Tokens e arquivos do piloto não são uma política de retenção de produção. Limites de autenticação guardam hashes pseudonimizados, não anônimos; buckets antigos são limpos no próximo processamento de autenticação.

Antes de uso público: definir controlador e contato, canal de direitos e atendimento, bases legais por finalidade, prazos de retenção e rotinas verificáveis de eliminação, segurança de backups e prevenção de restauração de dados excluídos, resposta a incidentes e política para dados de menores. A autodeclaração de 18 anos restringe o piloto, mas não é verificação de idade robusta nem resolve o fluxo de menores do produto ENEM.

Correção do e-mail cadastrado e atendimento aos demais direitos ainda precisam de fluxo próprio. A exclusão direta foi implementada para o piloto gratuito, sem registros financeiros: ao integrar Mercado Pago, avaliar retenções legais e não apagar registros necessários de obrigações/contestações sem análise. Há pedidos apenas no adaptador sandbox da próxima etapa, desabilitado por padrão. Contas com pedidos exigem análise de retenção e não são excluídas automaticamente; esse atendimento ainda precisa ser implementado. Não há compartilhamento de redações com OpenAI.

## Validação

Testes HTTP de confirmação, expiração, concorrência e uso único, reenvio, recuperação e revogação, exportação sem segredos, isolamento entre alunos, confirmação/senha/CSRF para exclusão, preservação dos demais usuários e bloqueio do cadastro HTTPS sem entrega configurada. Testes não enviam e-mails. QA manual dos formulários em navegador e celular permanece pendente; a prévia gerenciada anterior não encontrou o runtime Python.

## Referências para revisão jurídica

- ANPD — direitos dos titulares: https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados/direito-dos-titulares
- ANPD — guia de cookies: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-cookies-e-protecao-de-dados-pessoais.pdf

Esses mecanismos implementam parte dos requisitos; não certificam conformidade integral com a LGPD. Os avisos locais precisam ser substituídos por documentos revisados e completos antes do lançamento.
