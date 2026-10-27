/**
 * Textos das políticas do Mercado Nativo (Privacidade, Termos, Compras, Regras para Vendedores e Cookies).
 *
 * COMO ATUALIZAR
 * 1. Preencha os dados entre [colchetes] em EMPRESA (aparecem destacados no site até serem preenchidos).
 * 2. Ao mudar qualquer texto, aumente VERSAO e ATUALIZADO_EM aqui E a variável TERMOS_VERSAO no
 *    backend/.env (ou core/config.py). Assim o painel pede para os vendedores aceitarem a nova versão.
 * 3. {comissao}, {repasse} e {premium} são trocados pelos valores reais configurados no backend.
 *
 * Os textos foram escritos com base na LGPD (Lei 13.709/2018), no Código de Defesa do Consumidor
 * (Lei 8.078/1990), no Marco Civil da Internet (Lei 12.965/2014) e no Decreto 7.962/2013 (comércio
 * eletrônico). Antes de publicar o site de verdade, peça para um(a) advogado(a) revisar.
 */

export const VERSAO = '1.0'
export const ATUALIZADO_EM = '22 de outubro de 2026'

export const EMPRESA = {
  nome: 'Mercado Nativo',
  responsavel: 'Cleyton Luan Kramer Vieira',
  documento: '[CPF ou CNPJ do responsável]',
  cidade: 'Rio Branco – AC',
  endereco: '[endereço para correspondência]',
  email: '[e-mail de contato]',
  encarregado: 'Cleyton Luan Kramer Vieira',
  emailPrivacidade: '[e-mail do encarregado de dados]',
}

export interface Secao {
  titulo: string
  texto?: string[]
  itens?: string[]
}

export interface Politica {
  slug: string
  titulo: string
  icone: string
  resumo: string[]
  secoes: Secao[]
}

const contato = () =>
  `Fale com a equipe pelo e-mail ${EMPRESA.email} ou pela página Ajuda. Sobre dados pessoais, escreva para ${EMPRESA.emailPrivacidade}.`

export const POLITICAS: Politica[] = [
  // ------------------------------------------------------------------ PRIVACIDADE
  {
    slug: 'privacidade',
    titulo: 'Política de Privacidade',
    icone: 'lock',
    resumo: [
      'Pedimos só os dados necessários para vender, pagar e combinar a retirada.',
      'Não vendemos nem alugamos os seus dados para ninguém.',
      'Os dados do cartão são digitados no Mercado Pago e não passam pelo Mercado Nativo.',
      'Você pode ver, corrigir, baixar ou apagar os seus dados quando quiser.',
    ],
    secoes: [
      {
        titulo: '1. Quem cuida dos seus dados',
        texto: [
          `O ${EMPRESA.nome} é o controlador dos dados pessoais tratados no site (LGPD, art. 5º, VI). Responsável: ${EMPRESA.responsavel}, ${EMPRESA.documento}, ${EMPRESA.cidade}, ${EMPRESA.endereco}.`,
          `Encarregado(a) pelo tratamento de dados (LGPD, art. 41): ${EMPRESA.encarregado} — ${EMPRESA.emailPrivacidade}.`,
        ],
      },
      {
        titulo: '2. Quais dados coletamos',
        itens: [
          'Vendedores: nome, nome do sítio ou negócio, WhatsApp, e-mail (se informado), CEP, endereço, cidade e estado, foto de perfil, história, fotos e descrição dos produtos, e a ligação com a sua conta Mercado Pago (guardada de forma criptografada). Não guardamos dados bancários.',
          'Compradores: nome e WhatsApp informados na compra, produtos comprados, valores, forma de pagamento (Pix, crédito ou débito) e a situação do pedido. Não guardamos número de cartão, validade nem código de segurança.',
          'Avaliações: o nome e o comentário que você escrever ficam públicos na página do produto.',
          'Dados técnicos: endereço IP e horário de acesso, usados para segurança (por exemplo, limitar tentativas de login) e para contar visitas sem repetir a mesma pessoa. A contagem de visitas guarda o IP só por 30 minutos, na memória do servidor.',
          'No seu aparelho: favoritos, produtores seguidos, tamanho da letra e o login ficam guardados no próprio navegador (veja a Política de Cookies).',
        ],
      },
      {
        titulo: '3. Para que usamos e com qual base legal',
        itens: [
          'Criar e manter a conta do vendedor, mostrar os produtos na vitrine, processar pedidos e pagamentos e combinar a retirada — execução de contrato (LGPD, art. 7º, V).',
          'Guardar o histórico de pedidos e pagamentos e atender pedidos de autoridades — cumprimento de obrigação legal (art. 7º, II).',
          'Proteger o site contra fraudes e abusos, contar visitas e melhorar o serviço — legítimo interesse (art. 7º, IX), sempre usando o mínimo de dados.',
          'Mostrar o endereço completo do vendedor na vitrine — só se o próprio vendedor ligar essa opção no perfil (consentimento, art. 7º, I). Ele pode desligar quando quiser.',
          'Enviar avisos pelo WhatsApp sobre a conta e os pedidos (código de acesso, pedido pago, produto aprovado). Não enviamos propaganda.',
        ],
      },
      {
        titulo: '4. Com quem compartilhamos',
        itens: [
          'Entre comprador e vendedor: depois do pagamento, o vendedor recebe o nome e o WhatsApp do comprador, e o comprador recebe o contato do vendedor, para combinar a retirada.',
          'Mercado Pago: processa os pagamentos e a divisão dos valores. Tem a sua própria política de privacidade.',
          'WhatsApp (por meio da Evolution API): envio dos códigos de acesso e dos avisos de pedido.',
          'Mapas e CEP: o nome da cidade pode ser consultado no OpenStreetMap para calcular distâncias, e o CEP digitado no cadastro é consultado no ViaCEP para preencher o endereço.',
          'Sugestão de textos: as palavras digitadas no botão "Sugerir texto" são processadas por uma inteligência artificial instalada no próprio servidor. Se o serviço opcional Groq estiver ligado, só essas palavras são enviadas a ele (sem nome nem contato).',
          'Hospedagem e serviços de apoio do site (servidor, fontes de letra do Google e o tradutor VLibras), que podem receber o endereço IP para funcionar.',
          'Autoridades públicas, quando a lei ou uma ordem judicial exigir.',
          'Alguns desses serviços guardam dados fora do Brasil (transferência internacional — LGPD, art. 33). Usamos apenas empresas que oferecem proteção adequada.',
        ],
      },
      {
        titulo: '5. Por quanto tempo guardamos',
        itens: [
          'Conta do vendedor: enquanto ela estiver ativa.',
          'Quando a conta é excluída (pelo vendedor ou pela equipe): nome, WhatsApp, e-mail, endereço, foto, história e ligação com o Mercado Pago são apagados na hora. Produtos, fotos e avaliações também são apagados.',
          'Pedidos pagos: guardados por 5 anos, para cumprir obrigações legais e para a defesa em caso de reclamação (Código de Defesa do Consumidor, art. 27). Depois disso, são apagados ou anonimizados.',
          'Registros de acesso (IP, data e hora), quando existirem: 6 meses, como exige o Marco Civil da Internet (art. 15).',
        ],
      },
      {
        titulo: '6. Seus direitos',
        texto: ['Pela LGPD (art. 18), você pode pedir, de graça:'],
        itens: [
          'Confirmação de que tratamos os seus dados e acesso a eles.',
          'Correção de dados errados ou desatualizados.',
          'Anonimização, bloqueio ou eliminação de dados desnecessários.',
          'Uma cópia dos seus dados para levar a outro serviço (portabilidade).',
          'Saber com quem compartilhamos os seus dados.',
          'Retirar o consentimento, quando ele for a base legal (por exemplo, o endereço público).',
          'Vendedores fazem quase tudo sozinhos em "Meu perfil": corrigir dados, "Baixar meus dados" e "Excluir minha conta".',
          `Compradores e outros pedidos: escreva para ${EMPRESA.emailPrivacidade} informando o número do pedido. Respondemos em até 15 dias.`,
          'Se não ficar satisfeito, você pode reclamar na Autoridade Nacional de Proteção de Dados (ANPD), pelo site gov.br/anpd.',
        ],
      },
      {
        titulo: '7. Como protegemos os dados',
        itens: [
          'Acesso pelo código do WhatsApp, com limite de tentativas; senhas de administradores guardadas com criptografia.',
          'Ligação com o Mercado Pago guardada de forma criptografada; nenhum dado de cartão ou de conta bancária no nosso banco de dados.',
          'Fotos conferidas pelo conteúdo do arquivo antes de serem aceitas.',
          'Só a equipe autorizada acessa o painel administrativo.',
          'Se acontecer um incidente de segurança que possa causar risco ou dano, avisaremos as pessoas afetadas e a ANPD (LGPD, art. 48).',
        ],
      },
      {
        titulo: '8. Crianças e adolescentes',
        texto: [
          'Para vender é preciso ter 18 anos ou mais. Compras feitas por menores de idade devem ter o acompanhamento de um responsável. Não coletamos de propósito dados de crianças.',
        ],
      },
      {
        titulo: '9. Mudanças nesta política',
        texto: [
          'Quando esta política mudar, a data e a versão no fim da página serão atualizadas. Para os vendedores, o painel mostra o aviso e pede um novo aceite.',
          contato(),
        ],
      },
    ],
  },

  // ------------------------------------------------------------------ TERMOS
  {
    slug: 'termos',
    titulo: 'Termos de Uso',
    icone: 'book',
    resumo: [
      'O Mercado Nativo aproxima quem produz de quem compra na mesma região.',
      'Quem vende é o produtor: ele responde pela qualidade e pela entrega do que anuncia.',
      'Todo anúncio passa pela equipe antes de aparecer na vitrine.',
      'Ao usar o site, você concorda com estas regras.',
    ],
    secoes: [
      {
        titulo: '1. O que é o Mercado Nativo',
        texto: [
          `O ${EMPRESA.nome} (${EMPRESA.documento}, ${EMPRESA.cidade}) é uma plataforma na internet que mostra produtos de pequenos produtores rurais e artesãos e intermedeia o pagamento das compras. A venda é feita entre o comprador e o vendedor; a plataforma não é dona dos produtos.`,
        ],
      },
      {
        titulo: '2. Quem pode usar',
        itens: [
          'Qualquer pessoa pode ver a vitrine e comprar. Menores de 18 anos devem comprar com o acompanhamento de um responsável.',
          'Para vender é preciso ter 18 anos ou mais, ser o próprio produtor ou artesão (ou representar a família ou a associação que produz) e informar dados verdadeiros.',
        ],
      },
      {
        titulo: '3. Conta e acesso',
        itens: [
          'O vendedor entra com um código enviado ao WhatsApp cadastrado. Não existe senha.',
          'Não passe o código para ninguém. A equipe do Mercado Nativo nunca pede o código.',
          'O vendedor é responsável pelo que é feito com o seu número e deve avisar a equipe se perder o celular.',
        ],
      },
      {
        titulo: '4. Compromissos do vendedor',
        itens: [
          'Anunciar só o que produz ou faz, com fotos reais, descrição verdadeira, preço final e quantidade disponível atualizada.',
          'Cumprir as normas sanitárias, ambientais e fiscais que valem para o seu produto (por exemplo, vigilância sanitária, inspeção de produtos de origem animal e regras do IBAMA), e emitir nota fiscal quando a lei exigir.',
          'Atender o comprador com respeito, combinar a retirada e entregar exatamente o que foi vendido.',
          'Seguir as Regras para Vendedores e Produtos Proibidos.',
        ],
      },
      {
        titulo: '5. Compromissos do comprador',
        itens: [
          'Informar nome e WhatsApp corretos, para o vendedor conseguir falar com você.',
          'Combinar e fazer a retirada, ou avisar se desistir (veja a Política de Compras e Cancelamentos).',
          'Escrever avaliações verdadeiras e respeitosas.',
        ],
      },
      {
        titulo: '6. Curadoria e moderação',
        itens: [
          'Todo produto novo, e toda mudança de nome, descrição, história ou fotos, passa pela análise da equipe antes de aparecer na vitrine.',
          'A equipe pode pedir ajustes, recusar ou remover anúncios e encerrar contas que descumpram estes termos ou a lei. O vendedor é avisado pelo WhatsApp, com o motivo.',
          'Avaliações ofensivas, falsas ou com dados pessoais de outras pessoas podem ser removidas.',
        ],
      },
      {
        titulo: '7. Pagamentos, comissão e plano Premium',
        itens: [
          'Os pagamentos são processados pelo Mercado Pago (Pix, cartão de crédito ou débito).',
          'Em cada venda paga no site, o Mercado Nativo fica com {comissao}% do valor, e o vendedor recebe {repasse}%. O cadastro e os anúncios são gratuitos.',
          'O plano Premium é opcional, custa {premium} por 30 dias, não se renova sozinho e dá acesso à Calculadora de Custos e aos destaques na vitrine.',
        ],
      },
      {
        titulo: '8. Fotos e textos enviados',
        texto: [
          'O vendedor continua dono das fotos e dos textos que envia e autoriza o Mercado Nativo a mostrá-los no site e a usá-los para divulgar a plataforma enquanto o anúncio existir. É proibido enviar fotos ou textos de outras pessoas sem autorização.',
        ],
      },
      {
        titulo: '9. O que não é permitido',
        itens: [
          'Golpes, anúncios falsos, preços enganosos ou tentativas de enganar compradores e a equipe.',
          'Usar o site para vender produtos proibidos (veja as Regras para Vendedores).',
          'Tentar invadir, copiar em massa ou atrapalhar o funcionamento do site.',
          'Ofender, discriminar ou ameaçar qualquer pessoa.',
        ],
      },
      {
        titulo: '10. Responsabilidades',
        itens: [
          'O vendedor responde pela qualidade, segurança e legalidade dos produtos que anuncia.',
          'O Mercado Nativo ajuda a resolver problemas entre comprador e vendedor e cumpre o Código de Defesa do Consumidor. Nenhuma regra destes termos tira direitos garantidos por lei ao consumidor.',
          'Podemos fazer paradas para manutenção. Avisaremos quando for possível.',
        ],
      },
      {
        titulo: '11. Encerramento da conta',
        texto: [
          'O vendedor pode excluir a própria conta a qualquer momento em "Meu perfil". A equipe pode encerrar contas que descumpram estes termos. Em ambos os casos, os dados pessoais são apagados como descrito na Política de Privacidade.',
        ],
      },
      {
        titulo: '12. Leis e foro',
        texto: [
          'Estes termos seguem as leis do Brasil. O consumidor pode entrar com ação no foro do seu próprio domicílio (CDC, art. 101). Nos demais casos, fica escolhido o foro da Comarca de Rio Branco – AC.',
          contato(),
        ],
      },
    ],
  },

  // ------------------------------------------------------------------ COMPRAS
  {
    slug: 'compras',
    titulo: 'Compras, Pagamentos e Cancelamentos',
    icone: 'shopping-bag',
    resumo: [
      'Você paga com Pix, cartão de crédito ou débito, e retira o produto com o vendedor.',
      'Pode desistir em até 7 dias depois de retirar e receber o dinheiro de volta.',
      'Se o produto vier com problema, você tem direito a troca ou devolução do dinheiro.',
      'O dinheiro volta pelo mesmo meio usado no pagamento.',
    ],
    secoes: [
      {
        titulo: '1. Como funciona a compra',
        itens: [
          'Escolha o produto, a quantidade e informe o seu nome e o seu WhatsApp.',
          'Pague pelo site. Você recebe o resumo do pedido no WhatsApp.',
          'Combine com o vendedor o dia e o local da retirada pelo WhatsApp.',
          'O estoque é descontado sozinho quando o pagamento é confirmado.',
        ],
      },
      {
        titulo: '2. Formas de pagamento',
        itens: [
          'Pix: aprovação na hora. O código Pix tem prazo; se vencer, é só gerar um novo.',
          'Cartão de crédito em até 6 parcelas. Se houver juros, o Mercado Pago mostra o valor antes de você confirmar.',
          'Cartão de débito, à vista.',
          'Os dados do cartão são digitados no formulário do Mercado Pago e não passam pelo Mercado Nativo.',
          'Pedidos não pagos não reservam o produto.',
        ],
      },
      {
        titulo: '3. Retirada',
        itens: [
          'A retirada é feita com o vendedor, no local e no horário combinados pelo WhatsApp. Não fazemos entregas.',
          'Recomendamos combinar a retirada em até 7 dias depois do pagamento. Se não for possível retirar, você pode cancelar e receber o valor de volta.',
          'Na retirada, confira o produto e informe o número do pedido.',
        ],
      },
      {
        titulo: '4. Cancelar antes de retirar',
        texto: [
          'Enquanto o produto não foi retirado, você pode cancelar e receber 100% do valor pago. Avise o vendedor pelo WhatsApp ou fale com a equipe informando o número do pedido.',
        ],
      },
      {
        titulo: '5. Direito de arrependimento (7 dias)',
        texto: [
          'Como a compra é feita pela internet, você pode desistir em até 7 dias depois de retirar o produto, sem precisar explicar o motivo, e receber de volta todo o valor pago (Código de Defesa do Consumidor, art. 49).',
          'Combine a devolução com o vendedor. Para alimentos, faça isso o quanto antes e mantenha o produto bem guardado, para ele ainda estar em boas condições.',
        ],
      },
      {
        titulo: '6. Produto com problema',
        itens: [
          'Se o produto estiver estragado, com defeito ou diferente do anúncio, você pode reclamar em até 30 dias para alimentos e outros produtos que acabam com o uso, e em até 90 dias para artesanato e outros produtos duráveis (CDC, art. 26).',
          'Você pode escolher a troca por outro igual, a devolução do dinheiro ou um desconto proporcional (CDC, art. 18).',
          'Fale primeiro com o vendedor. Se não resolver, fale com a equipe informando o número do pedido e, se possível, mande fotos. Respondemos em até 5 dias úteis.',
        ],
      },
      {
        titulo: '7. Como o dinheiro volta',
        itens: [
          'Pix: o valor volta para a mesma conta de onde saiu.',
          'Cartão: o estorno aparece na fatura. O prazo depende do banco do cartão e pode levar até duas faturas.',
          'A devolução é feita pelo Mercado Pago, a pedido da equipe do Mercado Nativo.',
        ],
      },
      {
        titulo: '8. Plano Premium (para vendedores)',
        texto: [
          'O plano Premium custa {premium} por 30 dias e não se renova sozinho. O vendedor pode pedir o cancelamento com devolução do valor em até 7 dias depois da contratação.',
          contato(),
        ],
      },
    ],
  },

  // ------------------------------------------------------------------ VENDEDORES
  {
    slug: 'vendedores',
    titulo: 'Regras para Vendedores e Produtos Proibidos',
    icone: 'store',
    resumo: [
      'Venda só o que você produz ou faz, com fotos reais e preço final.',
      'Alguns produtos são proibidos, como bebidas alcoólicas, animais silvestres e remédios.',
      'A equipe confere cada anúncio antes de ir para a vitrine.',
      'Quem descumpre as regras pode ter o anúncio removido ou a conta encerrada.',
    ],
    secoes: [
      {
        titulo: '1. O que pode ser vendido',
        itens: [
          'Frutas, verduras, legumes, temperos e outros produtos da roça.',
          'Alimentos caseiros e artesanais (doces, geleias, farinhas, pães, polpas, cafés, chás), feitos com higiene e dentro da validade.',
          'Artesanato e peças feitas à mão (cestaria, cerâmica, crochê, madeira de origem legal, entre outros).',
          'Bebidas não alcoólicas, como sucos, polpas e chás.',
        ],
      },
      {
        titulo: '2. Produtos proibidos',
        itens: [
          'Bebidas alcoólicas de qualquer tipo.',
          'Animais vivos.',
          'Animais silvestres e qualquer parte ou produto deles (penas, couro, carne, ovos de tartaruga ou de tracajá etc.), e plantas protegidas sem autorização dos órgãos ambientais (Lei 9.605/1998).',
          'Madeira, lenha ou carvão sem comprovação de origem legal.',
          'Remédios, garrafadas, ervas ou qualquer produto vendido com promessa de cura ou tratamento de doença.',
          'Agrotóxicos, venenos, armas, munição, fogos de artifício, cigarros e tabaco.',
          'Produtos falsificados, de marcas de outras pessoas ou industrializados revendidos como se fossem artesanais.',
          'Alimentos vencidos, sem condições de higiene ou de origem animal sem a inspeção exigida por lei (por exemplo, SIM, SIE ou SIF para queijos, carnes e embutidos).',
          'Serviços, produtos digitais e qualquer coisa proibida por lei.',
        ],
      },
      {
        titulo: '3. Como deve ser o anúncio',
        itens: [
          'Fotos reais do seu produto, tiradas por você.',
          'Nome claro, preço final em reais e a quantidade que você realmente tem.',
          'Para alimentos: ingredientes, peso ou tamanho, validade e aviso de alergênicos (por exemplo, "contém leite", "contém glúten", "contém castanhas").',
          'Nada de textos ofensivos, discriminatórios ou com dados pessoais de outras pessoas.',
        ],
      },
      {
        titulo: '4. Curadoria',
        itens: [
          'Todo anúncio novo, e toda mudança de nome, descrição, história ou fotos, é analisado pela equipe antes de aparecer na vitrine. Mudanças só de preço, estoque ou lote valem na hora.',
          'Se faltar alguma coisa, a equipe pede o ajuste pelo WhatsApp, explicando o motivo.',
        ],
      },
      {
        titulo: '5. O que acontece se as regras não forem cumpridas',
        itens: [
          '1º: pedido de ajuste no anúncio.',
          '2º: remoção do anúncio, com aviso e motivo pelo WhatsApp.',
          '3º: encerramento da conta, em casos graves ou repetidos (por exemplo, golpe, produto proibido ou risco à saúde). Nesses casos a conta pode ser encerrada de imediato.',
        ],
      },
      {
        titulo: '6. Recebimentos',
        itens: [
          'Em cada venda paga pelo site você recebe {repasse}% do valor; o Mercado Nativo fica com {comissao}%.',
          'Conectando a sua conta Mercado Pago em "Meu perfil", o valor cai direto na sua conta. Nunca pedimos senha de banco.',
        ],
      },
      {
        titulo: '7. Avaliações e denúncias',
        texto: [
          'É proibido criar avaliações falsas, para você ou contra outros vendedores. Qualquer pessoa pode denunciar um anúncio ou vendedor pelo contato da equipe; analisamos todas as denúncias.',
          contato(),
        ],
      },
    ],
  },

  // ------------------------------------------------------------------ COOKIES
  {
    slug: 'cookies',
    titulo: 'Cookies e Dados no seu Aparelho',
    icone: 'settings',
    resumo: [
      'O Mercado Nativo não usa cookies de propaganda nem de rastreamento.',
      'Guardamos no seu navegador só o necessário: login, favoritos e tamanho da letra.',
      'Você pode apagar tudo isso quando quiser, nas configurações do navegador.',
    ],
    secoes: [
      {
        titulo: '1. O que fica guardado no seu navegador',
        itens: [
          'Login do vendedor ou do administrador (para não precisar entrar de novo a cada página). Some quando você toca em "Sair".',
          'Produtos favoritos e produtores que você segue.',
          'Tamanho da letra escolhido no botão "Aa".',
          'Essas informações ficam só no seu aparelho (armazenamento local do navegador) e não são usadas para propaganda.',
        ],
      },
      {
        titulo: '2. Serviços de outras empresas',
        itens: [
          'Mercado Pago: na hora do pagamento, o formulário do Mercado Pago pode usar cookies e informações do aparelho para segurança e prevenção de fraudes.',
          'Tradutor VLibras e fontes de letra do Google: recebem o endereço IP para funcionar.',
          'Cada uma dessas empresas tem a sua própria política de privacidade.',
        ],
      },
      {
        titulo: '3. Como apagar',
        texto: [
          'No navegador, abra as configurações e apague os "dados do site" ou o "histórico". Os favoritos e o tamanho da letra voltam ao normal, e será preciso entrar de novo.',
          contato(),
        ],
      },
    ],
  },
]

export function politica(slug: string): Politica | undefined {
  return POLITICAS.find((p) => p.slug === slug)
}
