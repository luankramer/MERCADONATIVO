# Histórico de alterações

Datas no horário de Rio Branco (AC).

## 16/11/2026: taxas claras e financeiro com repasses
- Termos e Regras para Vendedores v1.3: taxa do Mercado Pago (Pix ~0,99%, débito ~3,99%, crédito 2,95% a 4,98%), comissão de 10% e prazo do repasse.
- Formulário do produto mostra quanto o produtor recebe no Pix e no cartão.
- Pedidos do produtor mostram venda, taxa do Mercado Pago, comissão, valor líquido e se o repasse está pendente ou pago.
- Taxa real do Mercado Pago guardada em cada pagamento (fee_details); sem ela, estimativa pela tabela.
- Painel admin > Financeiro: resumo do mês, quanto entrou na conta do Mercado Nativo, repasses por produtor, registro do repasse e relatório para Excel.

## 15/11/2026: carregamento mais rápido e sem piscar
- Painel, perfil e edição de produto mostram blocos de carregamento até os dados chegarem (antes piscavam vazios).
- O painel busca os dados e os pedidos ao mesmo tempo.
- Site e API comprimidos (gzip/brotli): menos dados para baixar no celular.
- Fotos grandes já enviadas são reduzidas ao iniciar o backend (até 1200 px), mantendo o mesmo endereço.
- A importação mantém os administradores do servidor.

## 14/11/2026: publicação no Railway
- Recuperação de conta do admin ("Esqueci minha senha"): código de 6 números pelo WhatsApp e pelo e-mail cadastrados, válido por 10 minutos e com 5 tentativas; campo WhatsApp no cadastro dos administradores.
- Configuração dos serviços Backend e Site (`railway.json`) e guia `DEPLOY_RAILWAY.md`.
- Backend aceita o endereço do MySQL do Railway, usa o domínio público dele e guarda as fotos num volume.
- Primeiro acesso num servidor novo: Super Admin pela variável `ADMIN_INICIAL_SENHA` e dados de demonstração com `DADOS_DEMO=true`.
- Site servido por `servidor.mjs`, sem pacotes extras.
- Script `gerar_variaveis_railway.bat` monta as variáveis a partir dos `.env` locais, sem mostrar os segredos.
- `levar_dados_para_o_railway.bat`: leva o banco e as fotos deste computador para o site online (rota liberada só com `IMPORTACAO_LIBERADA=true`, para o Super Admin).

## 13/11/2026: pedido de cancelamento com aprovação da equipe
- Pedido não pago: o cliente cancela na hora. Pedido pago: a equipe confirma com o produtor antes de devolver.
- Painel admin com "Pedidos e SAC", contador, "Aprovar e devolver" e "Recusar" com motivo.
- SAC no rodapé de todas as páginas; termos e políticas v1.2 (CNPJ fictício, uso acadêmico).

## 03/11/2026: remoção da IA e tolerância a falhas
- Removida a geração de texto por IA (Ollama); a análise dos anúncios passa a ser por palavras-chave.
- Filas e reenvio automático para avisos do Mercado Pago e mensagens do WhatsApp.
- Código de login por e-mail e WhatsApp oficial da Meta como reservas; Pix de reserva.
- Reforços de segurança.

## 29/10/2026: SAC e confirmações
- Contatos do SAC configuráveis; janela de confirmação própria.

## 27/10/2026: Mercado Pago pelo WhatsApp e curadoria
- Link de uso único no WhatsApp para o produtor conectar o Mercado Pago.
- Verificação automática dos anúncios por palavras-chave.
- Scripts .bat de apoio (segurança, Mercado Pago, admin, testes).

## 26/10/2026: atualização do Mercado Nativo
- Envio do projeto completo para o GitHub.

## 26/08/2026: início
- Criação do repositório.
