# Mercado Nativo

Plataforma web para integração de pequenos produtores e artesãos ao mercado consumidor local.
**TCC — UniNorte 2026 | Cleyton Luan Kramer Vieira**

| Camada | Tecnologia |
|---|---|
| Front-end | Vue 3 + Vite + TypeScript + Tailwind CSS (`front-mercado/`) |
| Back-end | Python + FastAPI + SQLAlchemy (`backend/`) |
| Banco | MySQL (`mercado_nativo`) |
| Login do produtor | Código pelo WhatsApp (Evolution API) |
| Pagamentos | Mercado Pago: crédito, débito e Pix, com split automático 90/10 |

---

## 1. Como rodar

### Jeito rápido (Windows)
Antes da primeira vez, crie o banco vazio com `backend/database/criar_banco.sql` (as tabelas o
backend cria sozinho). Depois, na pasta **`scripts`**, dê dois cliques nesta ordem:
1. `iniciar_backend.bat` — cria/usa o `.venv` da raiz, instala as dependências e sobe a API (deixe a janela aberta)
2. `iniciar_frontend.bat` — abre o site em http://localhost:5173

Outros scripts da pasta `scripts`: `redefinir_admin.bat`, `configurar_mercadopago.bat`,
`rodar_testes.bat` e `atualizar_seguranca.bat`.

> **Um único ambiente Python:** o projeto usa só o `.venv` da **raiz** (`mercado_nativo_app\.venv`).
> Não crie outro dentro de `backend`. No VS Code, abra a pasta `mercado_nativo_app` (não a pasta
> de cima), aperte **Ctrl + Shift + P → "Python: Select Interpreter"** e escolha o `.venv` da raiz.

**Login do painel administrativo:** use o e-mail e a senha de administrador que você já tinha.
Não existe senha padrão. Para criar o primeiro acesso ou trocar a senha, rode `scripts\redefinir_admin.bat`:
ele pergunta o e-mail e a senha (mínimo 8 caracteres, não aparece na tela ao digitar).

### Abrir no celular (iPhone, Android, tablet)
1. Celular e computador no **mesmo Wi-Fi**.
2. Rode os dois `.bat`. A janela do backend mostra o **IPv4** do computador (ex.: `192.168.0.15`).
3. No celular, abra `http://192.168.0.15:5173`. O site descobre sozinho o endereço da API.
4. Na primeira vez o Windows pergunta sobre o firewall: permita em **redes privadas**.
5. Para instalar como app: no iPhone, Safari → Compartilhar → *Adicionar à Tela de Início*;
   no Android, Chrome → menu → *Instalar app*.

### Back-end (manual, no PowerShell)
```powershell
cd "C:\Users\cleyt\Documents\8 Periodo\mercado_nativo_app"
python -m venv .venv                                    # só na primeira vez (na RAIZ do projeto)
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
copy .env.example .env                                  # se ainda não existir; ajuste os valores
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Documentação interativa da API: http://127.0.0.1:8000/docs
- Na primeira execução as tabelas novas e as colunas que faltam são criadas **automaticamente**
  (`app/db/migrations.py`). Os produtos que já existiam continuam aparecendo na vitrine.
- Não há senha padrão de administrador: crie com `python -m app.reset_admin`.

**Dados de demonstração** (os mesmos dos protótipos — só insere se não houver produtos):
```powershell
..\.venv\Scripts\python.exe -m app.seed
```
Produtor demo: WhatsApp `(68) 9 9911-2233` (Doce Querência, Premium).

**Testes automatizados** (usam um banco SQLite temporário, não mexem no seu MySQL):
`scripts\rodar_testes.bat` ou `..\.venv\Scripts\python.exe -m pytest -q` dentro de `backend`.

### Front-end (manual)
```bash
cd front-mercado
npm install
copy .env.example .env            # opcional: VITE_API_URL (padrão http://127.0.0.1:8000)
npm run dev
```
Acesse http://localhost:5173

---

### Publicar na internet (Railway)

Site, backend e banco ficam num projeto só do Railway. O passo a passo está em [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md) e o histórico de mudanças em [CHANGELOG.md](CHANGELOG.md).

---

## 2. Telas (conforme os protótipos do TCC)

| Rota | Tela |
|---|---|
| `/` | Início |
| `/vitrine` | Vitrine com categorias, favoritos e filtros (estado, cidade, raio em km, "usar minha localização") |
| `/vitrine/produto/:id` | Produto: galeria, história, produtor, **Comprar**, **Reservar pelo WhatsApp**, avaliações |
| `/produtor/:id` | Perfil público do produtor ("Nossa Jornada") |
| `/pedido/:codigo` | Pagamento (crédito, débito ou Pix), confirmação e contato para retirada |
| `/login-produtor`, `/cadastro-produtor` | Login por código no WhatsApp e cadastro em 4 passos |
| `/painel` | Painel do produtor: visitas, contatos, conversão, receita, pedidos, estoque, Calculadora de Custos, plano Premium |
| `/painel/produto/novo`, `/painel/produto/:id` | Cadastro/edição com fotos e "A Alma do Produto" |
| `/painel/perfil` | Perfil, endereço (privacidade) e conexão com a conta Mercado Pago |
| `/admin/login` | Login administrativo |
| `/admin/visao-geral` | KPIs, volume, receita 10 %, repasse 90 %, assinaturas, atividade, extrato de split |
| `/admin/aprovacoes` | Curadoria com verificação automática por palavras-chave (aprovar/rejeitar com motivo) |
| `/admin/pedidos` | Pedidos e SAC: contato do comprador, cancelamento e devolução |
| `/admin/vitrine-premium` | Destaques dos assinantes e concessão de Premium |
| `/admin/administradores` | Equipe (só o Super Admin cadastra/edita/exclui) |

Regras implementadas:
- Produto novo entra como **pendente** e só vai para a vitrine após aprovação. Mudanças de nome,
  categoria, descrição, história ou fotos voltam para a curadoria; preço, estoque e lote não.
- **Estoque atualizado automaticamente** a cada pagamento confirmado.
- **Destaque** só para produtos aprovados de produtores Premium (aparecem primeiro na vitrine).
- **Calculadora de Custos** exclusiva Premium: custo total ÷ rendimento × (1 + margem).
- **Retirada no local**: a vitrine mostra só a cidade; o endereço completo aparece apenas se o
  produtor ligar essa opção no perfil.

---

## 3. Pagamentos (Mercado Pago)

Aceita **cartão de crédito (até 6x), cartão de débito e Pix** no mesmo formulário, que é o
formulário oficial do Mercado Pago (Payment Brick). O número do cartão é digitado em campos do
próprio Mercado Pago e vira um *token*: o Mercado Nativo nunca recebe nem guarda dados de cartão.

**Modo `simulado` (padrão, ideal para a banca):** não precisa de conta. O comprador escolhe Pix,
crédito ou débito numa tela de demonstração; o split, a baixa de estoque e o extrato funcionam.

**Modo real — passo a passo:**
1. Entre em https://www.mercadopago.com.br/developers/panel/app → **Criar aplicação**
   (tipo *Pagamentos online*, produto *Checkout Transparente*). As credenciais de teste já são
   geradas junto com a aplicação.
2. Dê dois cliques em **`scripts\configurar_mercadopago.bat`**, cole a *Public Key* e o *Access Token*
   (menu **Credenciais de teste**). Ele confere as chaves no Mercado Pago e grava no `backend/.env`
   (`PAYMENT_MODE=mercadopago`). O Access Token não aparece na tela.
3. Reinicie o `scripts\iniciar_backend.bat`. A janela deve mostrar `pagamentos: mercadopago`.
4. Teste uma compra com os cartões de teste (CVV `123`, validade `11/30`, CPF `12345678909`):

   | Cartão | Número |
   |---|---|
   | Mastercard crédito | 5480 8328 0103 3311 |
   | Visa crédito | 4235 6477 2802 5682 |
   | Elo débito | 5067 7667 8388 8311 |

   Nome do titular: `APRO` aprova, `OTHE` recusa, `CONT` fica pendente, `FUND` saldo insuficiente.
   Use um e-mail de comprador diferente do e-mail da sua conta Mercado Pago.
5. Para produção, rode o `.bat` de novo com as **Credenciais de produção** (`APP_USR-...`).

Outros comandos: `configurar_mercadopago.bat --testar` (confere as chaves salvas) e
`configurar_mercadopago.bat --simulado` (volta para a demonstração sem apagar as chaves).

**Split automático (90% direto na conta do produtor) — opcional:**
1. Na mesma aplicação, copie *Client ID* e *Client Secret* e cadastre a **URL de redirecionamento**
   `https://SEU-ENDERECO/api/v1/mercadopago/callback` (precisa ser HTTPS — use ngrok em testes).
2. Preencha `MP_CLIENT_ID`, `MP_CLIENT_SECRET`, `MP_REDIRECT_URI` e `FRONTEND_URL` no `.env`.
3. Cada produtor abre **Meu perfil → Onde você recebe → Conectar conta Mercado Pago**, faz login no
   site do Mercado Pago e autoriza. A partir daí, cada venda cai na conta dele e a plataforma recebe
   a comissão (`application_fee`) automaticamente. Sem conectar, a venda entra na conta da
   plataforma e o repasse fica registrado no extrato do admin.

**Confirmação do Pix (webhook):** com `PUBLIC_API_URL` apontando para um endereço HTTPS (ngrok),
cadastre em *Webhooks* o evento **Pagamentos** e cole a *assinatura secreta* em `MP_WEBHOOK_SECRET`.
Mesmo sem webhook, a tela do pedido consulta o Mercado Pago a cada 5 segundos.

---

## 3.1 Cancelamento e devolução

| Quem cancela | Quando | Como |
|---|---|---|
| **Cliente** (não pago) | Antes de pagar | Na página do pedido: "Quero cancelar este pedido" + os 4 últimos números do WhatsApp da compra. Cancela na hora. |
| **Cliente** (pago, ou retirado nos 7 dias) | Antes de retirar, ou até 7 dias depois | Mesmo botão, mas vira um **pedido de cancelamento** para a equipe (nada é devolvido ainda) |
| **Produtor** | Antes de retirar | Painel → Pedidos para entregar → "Não consigo entregar" (motivo obrigatório) |
| **Equipe (admin)** | A qualquer momento | Admin → **Pedidos e SAC** → "Aprovar e devolver" / "Recusar" (pedidos do cliente) ou "Cancelar e devolver" |

**Pedido de cancelamento (pedido pago):** o produto pode já ter sido entregue ou enviado sem o
produtor ter marcado no painel. Por isso o cliente só *pede*: o pedido fica "pendente", o produtor
vê um aviso amarelo no painel e recebe WhatsApp, e a equipe vê o número no menu **Pedidos e SAC**
(filtro "Pedidos de cancelamento", com o WhatsApp do cliente e do vendedor). A equipe fala com o
produtor e então **aprova** (cancela e devolve) ou **recusa** com o motivo, que o cliente recebe no
WhatsApp. Depois de uma recusa, o cliente só continua pelo SAC.

Ao cancelar (ou aprovar o cancelamento de) um pedido pago, o sistema pede ao Mercado Pago a devolução **total**
(`POST /v1/payments/{id}/refunds`; no split, sai da conta do produtor). Se a devolução falhar,
o pedido **não** é cancelado. Depois: o estoque volta, o pedido fica "cancelado" e cliente e
produtor recebem aviso no WhatsApp. Pedido não pago: o Pix pendente é invalidado.
Se o produtor devolver pelo app do Mercado Pago, o aviso do webhook cancela o pedido sozinho.
Código: `backend/app/services/cancelamento_service.py`.

**SAC no rodapé:** preencha no `front-mercado/.env` e reinicie o `iniciar_frontend.bat`:
```
VITE_SUPORTE_WHATSAPP=68999999999
VITE_SUPORTE_TELEFONE=6833334444
VITE_SUPORTE_EMAIL=contato@exemplo.com
```
As políticas (versão 1.2) usam um **CNPJ fictício** e o endereço BR-317, km 18, Rio Branco – AC
(`front-mercado/src/content/politicas.ts`, objeto `EMPRESA`). Troque pelos dados reais antes de
publicar o site de verdade.

## 3.2 Acessibilidade (público mais velho e da zona rural)

- Letra maior em todo o site (texto normal de 18 px, nada abaixo de 14 px) e botão **"Aa Letra"**
  no topo para escolher Normal, Grande ou Maior (fica guardado no aparelho).
- Mais contraste, botões de no mínimo 48 px e ícones sempre com nome.
- Avisos ficam 8 segundos na tela e têm botão de fechar; confirmações ("Excluir produto?") usam
  uma janela própria com botões grandes "Sim, excluir" / "Não, manter".
- Busca sem acento, com nomes regionais (macaxeira = mandioca, jerimum = abóbora) e tolerante a
  erros de digitação (`app/services/busca_service.py` — para incluir sinônimos, edite a lista `SINONIMOS`).
- Compra em passos numerados ("Passo 2 de 3"), Pix guiado com botão "Copiar código Pix" e tela
  final explicando como retirar. O comprador recebe o resumo do pedido no WhatsApp.
- Botão **"Ouvir a descrição"** na página do produto (voz do próprio aparelho, sem internet extra).
- Cadastro do produtor em 4 etapas, foto direto pela câmera (reduzida antes de enviar, ideal para
  internet fraca), dica para ditar o texto pelo microfone do teclado.
- Painel do produtor em linguagem simples ("De cada 100 pessoas que viram, 6 chamaram você").
- Tradutor de Libras **VLibras** (governo federal), aviso de "Sem internet" e página **/ajuda**.
  Para mostrar o botão "Falar com a equipe" na Ajuda, preencha `VITE_SUPORTE_WHATSAPP` em
  `front-mercado/.env` (só números, com DDD) e reinicie o front-end.

**Voltar à versão anterior:** veja a seção "Backups" no fim deste arquivo.

---

## 3.3 Exclusões e políticas (LGPD)

- **Admin → Aprovações:** botão **Excluir** em cada publicação (também dentro de "Analisar"). Pede um
  motivo, que é enviado ao vendedor pelo WhatsApp. Fotos e avaliações são apagadas; pedidos antigos
  continuam no histórico.
- **Admin → Vendedores:** lista com busca. Só o **Super Admin** pode excluir um vendedor: os produtos
  saem da vitrine e os dados pessoais são apagados na hora (`app/services/remocao_service.py`). O
  cadastro vira "Vendedor removido" para não quebrar o histórico financeiro dos pedidos pagos.
- **Produtor → Meu perfil → Privacidade e seus dados:** "Baixar meus dados" (arquivo JSON) e
  "Excluir minha conta".
- **Políticas** em `/politicas/...`: Privacidade, Termos de Uso, Compras e Cancelamentos, Regras para
  Vendedores e Produtos Proibidos, Cookies. Links no rodapé, na Ajuda, no cadastro e na compra.
- O cadastro do produtor exige marcar o aceite (data e versão ficam gravadas). Cadastros antigos veem
  um aviso no painel para ler e aceitar.
- **Para editar os textos:** `front-mercado/src/content/politicas.ts`. Preencha os campos entre
  [colchetes] (CPF/CNPJ, endereço, e-mails) — eles aparecem destacados em amarelo até serem
  preenchidos. Ao mudar o texto, aumente `VERSAO` nesse arquivo e `TERMOS_VERSAO` no `backend/.env`.
- Os textos seguem a LGPD, o CDC, o Marco Civil e o Decreto 7.962/2013, mas **devem ser revisados por
  um(a) advogado(a)** antes de o site ir ao ar de verdade.

**Voltar à versão anterior:** veja a seção "Backups" no fim deste arquivo.

---

## 3.4 Segurança

- **Sem dados de cartão e sem dados bancários** no banco. Dados bancários de versões anteriores
  são apagados automaticamente ao iniciar.
- Tokens do Mercado Pago dos produtores ficam **criptografados** (Fernet/AES).
- O **valor** da compra é sempre calculado no servidor; o navegador não consegue alterá-lo.
- Webhook validado pela assinatura `x-signature` e o status é **reconsultado** na API antes de
  confirmar qualquer pagamento. Cada cobrança usa `X-Idempotency-Key` (evita cobrar duas vezes).
- Link do pedido com **código aleatório** (`/pedido/Xy8…`), impossível de adivinhar; a página não
  mostra telefone nem e-mail do comprador.
- Login do produtor por código no WhatsApp: o código **nunca vai para o navegador**
  (no modo desenvolvimento aparece só na janela do backend), expira em 5 min e só vale no
  navegador que pediu (campo `desafio`). Limites por IP, por número e no máximo 30 erros por
  número em 24 h. Trocar o número do WhatsApp exige um código enviado ao **novo** número e
  derruba as sessões abertas no número antigo.
- Admin: sem senha padrão, mínimo de 8 caracteres, bloqueio após 5 erros (15 min), sessão de 8 h.
- Limite de requisições em cadastro, avaliações, checkout, sugestão de texto e contatos.
- Uploads conferidos pelo **conteúdo real** do arquivo (não pela extensão), com tamanho máximo.
- Cabeçalhos de segurança (`nosniff`, `X-Frame-Options`, `Referrer-Policy`, HSTS em HTTPS).
- `APP_ENV=producao` desliga a documentação `/docs` e restringe o CORS aos endereços do `.env`.

---

## 3.6 Taxas e repasses

- O produtor recebe: **venda − taxa do Mercado Pago − comissão do Mercado Nativo (10%)**.
- Taxa do Mercado Pago: a real vem do próprio pagamento (`fee_details`); sem ela, usa a estimativa de
  `TAXA_MP_PIX`, `TAXA_MP_CREDITO` e `TAXA_MP_DEBITO` no `.env` (tabela oficial de nov/2026).
- Produtor com a conta Mercado Pago conectada recebe direto (split). Sem conta conectada, o dinheiro cai na
  conta do Mercado Nativo e é repassado até o 5º dia útil do mês seguinte.
- **Painel admin > Financeiro**: escolha o mês, veja o que entrou, as taxas, quanto repassar a cada produtor,
  registre o repasse depois de fazer o Pix e baixe o relatório para o Excel.

---

## 3.5 Esqueci a senha do admin

Na tela `/admin/login`, toque em **Esqueci minha senha**. O código de 6 números vai para o WhatsApp do
administrador (cadastrado em *Gestão de Administradores*; para o Super Admin também vale o
`ADMIN_MASTER_WHATSAPP` do `.env`) e para o e-mail, se o SMTP estiver configurado. O código vale 10 minutos
e aceita 5 tentativas. Sem acesso ao WhatsApp, no computador do servidor use `redefinir_admin.bat`.

---

## 4. WhatsApp (login por código)

Configure `EVOLUTION_BASE_URL`, `EVOLUTION_TOKEN` e `EVOLUTION_INSTANCE` no `.env`.
Com `OTP_DEV_MODE=true`, se o WhatsApp estiver fora do ar o código aparece **na janela do backend**
(nunca no navegador). Em produção use `OTP_DEV_MODE=false`.

Rotas de reserva (todas automáticas, configure no `.env`):

1. **Evolution API** (principal).
2. **API oficial da Meta** (`META_WA_*`): usada quando a Evolution não responde. Para o código de
   login, cadastre um modelo da categoria *Autenticação* e informe em `META_WA_TEMPLATE_CODIGO`.
3. **E-mail** (`SMTP_*`): na tela de login aparece "Receber no meu e-mail cadastrado".
4. **Fila de reenvio**: avisos de pedido que não saíram ficam na tabela `mensagens_pendentes` e
   são reenviados com espera crescente por até 24 h.

---

## 4.1 Se o Mercado Pago cair

- Cada chamada tem tempo limite e nova tentativa com a mesma chave de idempotência (não cobra duas vezes).
- Depois de 3 falhas seguidas o Mercado Pago é **pausado** por 60 s: as páginas não travam esperando.
- Com `PIX_RESERVA_CHAVE` configurada, o cliente vê o **Pix de reserva** (Pix Copia e Cola da conta do
  Mercado Nativo com valor e identificação `MN<nº>`). A equipe confere no extrato e clica
  **Confirmar Pix recebido** em Pedidos. O repasse ao produtor desse pedido é manual.
- Avisos (webhooks) que falharam vão para a fila `notificacoes_pagamento` e são reprocessados.
- A cada 2 min as tarefas automáticas conferem Pix pendentes, recuperam cobranças cuja resposta se
  perdeu (busca pela referência do pedido) e acompanham devoluções em andamento.
- Se um pagamento for aprovado depois de o pedido ter sido cancelado, o valor é devolvido sozinho.
- O painel Pedidos mostra a situação dos serviços (`GET /api/v1/admin/status-servicos`).

---

## 5. Estrutura de pastas (padrão para novos módulos)

```
mercado_nativo_app/
├── .venv/           → o ÚNICO ambiente Python do projeto
├── backend/         → API FastAPI (detalhes abaixo)
│   └── database/    → criar_banco.sql (cria o banco vazio)
├── front-mercado/   → site Vue 3 (detalhes abaixo)
├── identidade-visual/ → logo em SVG e PNG
├── scripts/         → .bat para iniciar, testar e configurar (dois cliques)
├── _backups/        → zips das versões anteriores (não vão para o Git)
├── .gitignore
└── README.md

backend/app/
├── api/v1/          → rotas (um arquivo por módulo: products.py, checkout.py, admin.py...)
├── core/            → config.py (.env), security.py (JWT, senhas), crypto.py, rate_limit.py
├── db/              → database.py e migrations.py (migração automática)
├── models/          → tabelas (*_model.py) — registre novos modelos em models/__init__.py
├── schemas/         → validação de entrada (Pydantic)
├── services/        → regras e integrações (*_service.py: curadoria, payment, checkout, order, whatsapp, geo...)
└── seed.py          → dados de demonstração
backend/tests/       → pytest

front-mercado/src/
├── views/           → telas (uma por rota)
├── components/
│   ├── ui/          → peças reutilizáveis (Icon, Modal, Toggle, StarRating, PixPayment, BottomNav...)
│   ├── catalog/     → vitrine (ProductCard, FilterModal, CheckoutModal...)
│   ├── producer/    → painel do produtor (CostCalculatorModal, PremiumModal)
│   ├── payment/     → PaymentStep, PaymentBrick (Mercado Pago), DemoPayment
│   └── admin/       → abas do admin (*Tab.vue, AnalyzeModal)
├── services/        → api.ts (HTTP + token), auth.ts (sessão), toast.ts, preferences.ts
├── content/         → textos das políticas (politicas.ts)
├── utils/           → format.ts (moeda, máscaras, ViaCEP), categorias.ts, imagem.ts
└── router/index.ts  → rotas e proteção de login
```

**Para criar um módulo novo:** modelo em `models/xxx_model.py` (+ import em `models/__init__.py`),
schema em `schemas/xxx.py`, rotas em `api/v1/xxx.py` (+ `include_router` no `main.py`), tela em
`views/XxxView.vue` (+ rota em `router/index.ts`) usando `api()` de `services/api.ts`.

---

## 6. Backups

Os zips ficam em `_backups/`:

| Arquivo | O que tem |
|---|---|
| `_backup_antes_ux_2026-10-21.zip` | sistema antes das melhorias de acessibilidade |
| `_backup_antes_politicas_2026-10-22.zip` | sistema antes da exclusão de vendedores e das políticas |
| `versao_antiga_Mercado_Nativo_ago2026.zip` | primeira versão do projeto (agosto/2026), só o código |

**Para voltar a um backup:** feche o backend e o front-end, extraia o zip dentro de `_backups/` e dê dois
cliques no `RESTAURAR_ESTE_BACKUP.bat` que estiver dentro da pasta extraída. As fotos enviadas, o
`node_modules` e o `.venv` não são mexidos. Os zips dos backups contêm o `backend/.env` (senhas):
não envie para ninguém.
