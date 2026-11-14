<script setup lang="ts">
/** Ajuda: passo a passo simples para comprar, pagar e vender, e perguntas comuns. */
import Icon from '@/components/ui/Icon.vue'
import { linkWhatsappSac } from '@/utils/suporte'
import SiteRodape from '@/components/ui/SiteRodape.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import BottomNav from '@/components/ui/BottomNav.vue'
import { POLITICAS } from '@/content/politicas'

const linkSuporte = linkWhatsappSac('Olá! Preciso de ajuda com o Mercado Nativo.')

const COMPRAR = [
  { icone: 'search', titulo: 'Escolha o produto', texto: 'Na página inicial, procure pelo nome ou toque em uma categoria, como "Frutas e verduras".' },
  { icone: 'shopping-bag', titulo: 'Toque em "Comprar"', texto: 'Escolha a quantidade, escreva seu nome e seu WhatsApp e pague com Pix, cartão de crédito ou de débito.' },
  { icone: 'phone', titulo: 'Combine a retirada', texto: 'Depois de pagar, toque em "Combinar a retirada pelo WhatsApp" e marque o dia com o produtor.' },
]
const VENDER = [
  { icone: 'user', titulo: 'Faça o cadastro', texto: 'Toque em "Sou produtor" e responda 4 perguntas simples. Não precisa de senha.' },
  { icone: 'camera', titulo: 'Anuncie o produto', texto: 'Tire uma foto, escreva o preço e a quantidade. A equipe confere e coloca na vitrine.' },
  { icone: 'wallet', titulo: 'Receba os pedidos', texto: 'Você recebe um aviso no WhatsApp a cada venda paga e combina a entrega com o comprador.' },
]
const PERGUNTAS = [
  { p: 'Preciso criar senha?', r: 'Não. Para entrar, você recebe um código de 6 números no seu WhatsApp.' },
  { p: 'Como pago com Pix?', r: 'Na hora de pagar, escolha Pix e toque em "Copiar código Pix". Abra o aplicativo do seu banco, escolha "Pix Copia e Cola", cole o código e confirme. A tela do pedido atualiza sozinha.' },
  { p: 'O produto é entregue em casa?', r: 'Não. A retirada é feita com o produtor. Depois de pagar, vocês combinam o dia e o local pelo WhatsApp.' },
  { p: 'Meus dados do cartão ficam guardados?', r: 'Não. O cartão é digitado no formulário do Mercado Pago, e o Mercado Nativo não recebe nem guarda esses dados.' },
  { p: 'A letra está pequena. O que faço?', r: 'Toque no botão "Aa Letra", no alto da tela, e escolha "Grande" ou "Maior".' },
  { p: 'Perdi o link do meu pedido.', r: 'Depois do pagamento, enviamos um resumo do pedido com o link para o seu WhatsApp.' },
  { p: 'Como cancelo uma compra?', r: 'Abra o link do pedido (ele chega no seu WhatsApp), toque em "Quero cancelar este pedido", digite os 4 últimos números do seu WhatsApp e confirme. Se ainda não pagou, cancela na hora. Se já pagou, a equipe confirma com o vendedor se o produto ainda não foi entregue e te responde pelo WhatsApp. Aprovado, o dinheiro volta sozinho: Pix em poucos minutos; no cartão, conforme o prazo do banco.' },
  { p: 'Já retirei o produto. Ainda posso desistir?', r: 'Sim, em até 7 dias depois de retirar. Peça pelo link do pedido ("Quero cancelar este pedido") ou fale com o SAC (no rodapé da página) informando o número do pedido. A equipe combina a devolução do produto e do dinheiro.' },
  { p: 'Vendedor: o cliente pediu para cancelar. O que faço?', r: 'Aparece um aviso amarelo no pedido, no seu painel. A equipe do Mercado Nativo vai falar com você para saber se o produto já foi entregue ou enviado. Se ainda não entregou, espere a confirmação antes de entregar.' },
  { p: 'Vendedor: e se eu não puder entregar um pedido?', r: 'No seu painel, em "Pedidos para entregar", toque em "Não consigo entregar" e escreva o motivo. O cliente recebe o dinheiro de volta e o produto volta para o seu estoque.' },
  { p: 'Vendedor: como recebo direto no Mercado Pago?', r: 'Em "Meu perfil", toque em "Mandar link no meu WhatsApp". Abra o link no celular, entre na sua conta do Mercado Pago e toque em "Autorizar". A equipe também pode mandar esse link para você.' },
  { p: 'Vendedor: não sei a senha do Mercado Pago.', r: 'Você não precisa dela. Na tela de entrada do Mercado Pago, escolha receber um código pelo WhatsApp ou SMS. Se trocou de número, toque em "Não consigo iniciar sessão".' },
  { p: 'Como apago os meus dados?', r: 'Vendedores: em "Meu perfil", toque em "Excluir minha conta" (ou "Baixar meus dados" para ter uma cópia). Compradores: fale com a equipe informando o número do pedido.' },
]
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <PublicHeader />
    <main class="max-w-3xl mx-auto px-4 py-6 sm:py-10 mb-nav space-y-10">
      <header>
        <h1 class="font-serif text-3xl sm:text-4xl font-bold text-slate-900">Precisa de ajuda?</h1>
        <p class="text-lg text-slate-700 mt-2">Veja abaixo como comprar e como vender. É simples, e você pode voltar aqui quando quiser.</p>
        <a v-if="linkSuporte" :href="linkSuporte" target="_blank" rel="noopener" class="btn-primary mt-5 text-lg px-6">
          <Icon name="phone" class="w-6 h-6" /> Falar com a equipe pelo WhatsApp
        </a>
      </header>

      <section aria-labelledby="ajuda-comprar">
        <h2 id="ajuda-comprar" class="font-serif text-2xl font-bold text-slate-900 mb-4">Como comprar</h2>
        <ol class="space-y-3">
          <li v-for="(p, i) in COMPRAR" :key="p.titulo" class="card p-5 flex gap-4">
            <span class="w-14 h-14 shrink-0 rounded-2xl bg-nativo-light text-nativo flex items-center justify-center"><Icon :name="p.icone" class="w-7 h-7" /></span>
            <span>
              <span class="block text-lg font-bold text-slate-900">{{ i + 1 }}. {{ p.titulo }}</span>
              <span class="block text-slate-700 mt-1">{{ p.texto }}</span>
            </span>
          </li>
        </ol>
        <RouterLink to="/" class="btn-outline mt-4">Ver os produtos</RouterLink>
      </section>

      <section aria-labelledby="ajuda-vender">
        <h2 id="ajuda-vender" class="font-serif text-2xl font-bold text-slate-900 mb-4">Como vender</h2>
        <ol class="space-y-3">
          <li v-for="(p, i) in VENDER" :key="p.titulo" class="card p-5 flex gap-4">
            <span class="w-14 h-14 shrink-0 rounded-2xl bg-terra-light text-terra flex items-center justify-center"><Icon :name="p.icone" class="w-7 h-7" /></span>
            <span>
              <span class="block text-lg font-bold text-slate-900">{{ i + 1 }}. {{ p.titulo }}</span>
              <span class="block text-slate-700 mt-1">{{ p.texto }}</span>
            </span>
          </li>
        </ol>
        <RouterLink to="/cadastro-produtor" class="btn rounded-xl px-6 mt-4 bg-terra text-white hover:bg-terra-dark">Quero vender</RouterLink>
      </section>

      <section aria-labelledby="ajuda-politicas">
        <h2 id="ajuda-politicas" class="font-serif text-2xl font-bold text-slate-900 mb-4">Regras e políticas</h2>
        <div class="grid sm:grid-cols-2 gap-3">
          <RouterLink v-for="p in POLITICAS" :key="p.slug" :to="`/politicas/${p.slug}`" class="card p-4 flex items-center gap-3 font-semibold text-slate-800 hover:border-nativo min-h-[64px]">
            <Icon :name="p.icone" class="w-6 h-6 text-nativo shrink-0" /> {{ p.titulo }}
          </RouterLink>
        </div>
      </section>

      <section aria-labelledby="ajuda-perguntas">
        <h2 id="ajuda-perguntas" class="font-serif text-2xl font-bold text-slate-900 mb-4">Perguntas comuns</h2>
        <div class="space-y-3">
          <details v-for="q in PERGUNTAS" :key="q.p" class="card p-5 group">
            <summary class="cursor-pointer text-lg font-semibold text-slate-900 flex items-center justify-between gap-3 min-h-[32px]">
              {{ q.p }} <Icon name="plus" class="w-6 h-6 shrink-0 text-nativo group-open:rotate-45 transition" />
            </summary>
            <p class="text-slate-700 mt-3 leading-relaxed">{{ q.r }}</p>
          </details>
        </div>
      </section>
      <SiteRodape mensagem="Olá! Vim pela página de Ajuda e preciso de ajuda com o Mercado Nativo." />
    </main>
    <BottomNav variante="publico" />
  </div>
</template>
