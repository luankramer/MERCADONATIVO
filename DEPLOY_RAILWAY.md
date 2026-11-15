# Publicar o Mercado Nativo no Railway

Tudo fica num projeto só do Railway, com 3 serviços:

| Serviço | O que é | Pasta do repositório |
|---|---|---|
| **MySQL** | Banco de dados | (modelo pronto do Railway) |
| **Backend** | API FastAPI | `backend` (config: `/backend/railway.json`) |
| **Site** | Telas em Vue (também vira atalho no celular) | `front-mercado` (config: `/front-mercado/railway.json`) |

O WhatsApp continua no servidor da Evolution API que já é usado hoje. O backend só precisa das
mesmas variáveis `EVOLUTION_*`.

**Custo:** o teste grátis do Railway dá US$ 5 de crédito por 30 dias. A semana da apresentação
gasta por volta de US$ 3 (estimativa). Detalhes na planilha de custos.

## Passo a passo

1. **Conta:** entre em railway.com com **Login with GitHub**. A conta fica verificada; sem isso o
   teste limita a internet de saída e o Mercado Pago e o WhatsApp não funcionam.
2. **Projeto e backend:** *New Project* > *Deploy from GitHub repo* > `MERCADONATIVO`.
   Renomeie o serviço para **Backend**. Em *Settings*:
   - *Source* > *Root Directory*: `/backend`
   - *Config-as-code* > *Railway Config File*: `/backend/railway.json`
3. **Banco:** no projeto, *+ Create* > *Database* > *MySQL*. Deixe o nome **MySQL**.
4. **Site:** *+ Create* > *GitHub Repo* > `MERCADONATIVO` de novo. Renomeie para **Site**.
   - *Root Directory*: `/front-mercado`
   - *Railway Config File*: `/front-mercado/railway.json`
5. **Endereços:** em *Settings* > *Networking* > *Generate Domain*, no **Backend** e no **Site**.
6. **Fotos dos produtos:** no **Backend**, adicione um *Volume* com *Mount Path* `/data`.
   Sem o volume, as fotos somem a cada nova publicação.
7. **Variáveis:** no seu computador, rode `scripts\gerar_variaveis_railway.bat`. Ele cria, na
   pasta `backend`, dois arquivos que não vão para o GitHub:
   - `railway-backend.env.local`: cole em **Backend** > *Variables* > *Raw Editor*.
   - `railway-site.env.local`: cole em **Site** > *Variables* > *Raw Editor*.

   No Backend, preencha `ADMIN_INICIAL_SENHA` (mínimo 8 caracteres): é a senha do primeiro
   acesso do Super Admin (`ADMIN_MASTER_EMAIL`). Depois de entrar, apague essa variável.
8. **Publicar:** clique em *Deploy* nos serviços. No log do Backend deve aparecer
   `✅ Mercado Nativo API pronta`. Na primeira vez, com `DADOS_DEMO=true`, ele cadastra os
   produtores e produtos de demonstração.
9. **Mercado Pago** (painel do aplicativo, em mercadopago.com.br/developers):
   - URL de redirecionamento: `https://ENDERECO-DO-BACKEND/api/v1/mercadopago/callback`
   - Notificações (webhook): `https://ENDERECO-DO-BACKEND/api/v1/checkout/webhook/mercadopago`
10. **Teste completo** (de preferência pelo celular, fora do Wi-Fi):
    - abrir o site e "Adicionar à tela inicial";
    - entrar como produtor com o código do WhatsApp;
    - comprar com o cartão de teste e ver o pedido no painel;
    - entrar no `/admin/login` com o e-mail do Super Admin.

## Levar os dados deste computador (em vez dos dados de demonstração)

1. No Railway, no **Backend**, deixe `DADOS_DEMO=false` e `IMPORTACAO_LIBERADA=true`.
2. Com o MySQL deste computador ligado, rode `scripts\levar_dados_para_o_railway.bat`.
   Ele exporta o banco e as fotos, pede o e-mail e a senha do Super Admin **online** e envia tudo.
3. O banco online é trocado pelo deste computador: produtores, produtos, pedidos e fotos.
   Os administradores online continuam os mesmos (o login de admin online não muda).
4. Depois, apague `IMPORTACAO_LIBERADA` no Railway.

## O que o código já faz sozinho

- `DATABASE_URL=${{MySQL.MYSQL_URL}}`: o prefixo `mysql://` vira `mysql+pymysql://`.
- `PUBLIC_API_URL` vazio: usa o domínio do Railway (`RAILWAY_PUBLIC_DOMAIN`).
- `MP_REDIRECT_URI` vazio: monta `PUBLIC_API_URL/api/v1/mercadopago/callback`.
- `FRONTEND_URL` entra sozinho na lista de sites que podem chamar a API (CORS).
- Tabelas e colunas são criadas na primeira vez que o backend sobe.
- O site é servido por `front-mercado/servidor.mjs` (sem pacotes extras), com as rotas do Vue.

## Depois da apresentação

Para não gastar crédito nem deixar dados no ar: *Settings* do projeto > *Delete Project*.
