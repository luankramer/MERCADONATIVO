# Histórico de alterações

Datas no horário de Rio Branco (AC).

## 14/11/2026: publicação no Railway
- Configuração dos serviços Backend e Site (`railway.json`) e guia `DEPLOY_RAILWAY.md`.
- Backend aceita o endereço do MySQL do Railway, usa o domínio público dele e guarda as fotos num volume.
- Primeiro acesso num servidor novo: Super Admin pela variável `ADMIN_INICIAL_SENHA` e dados de demonstração com `DADOS_DEMO=true`.
- Site servido por `servidor.mjs`, sem pacotes extras.
- Script `gerar_variaveis_railway.bat` monta as variáveis a partir dos `.env` locais, sem mostrar os segredos.

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
