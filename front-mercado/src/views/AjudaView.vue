<script setup lang="ts">
/** Ajuda: passo a passo simples para comprar, pagar e vender, e perguntas comuns. */
import Icon from '@/components/ui/Icon.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import BottomNav from '@/components/ui/BottomNav.vue'
import { POLITICAS } from '@/content/politicas'

// Número da equipe vem do front-mercado/.env (VITE_SUPORTE_WHATSAPP). Sem número, o botão não aparece.
const suporte = (import.meta.env.VITE_SUPORTE_WHATSAPP as string | undefined)?.replace(/\D/g, '') || ''
const linkSuporte = suporte
  ? `https://wa.me/55${suporte}?text=${encodeURIComponent('Olá! Preciso de ajuda com o Mercado Nativo.')}`
  : ''

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
  { p: 'Posso desistir da compra?', r: 'Sim. Antes de retirar, você cancela e recebe tudo de volta. Depois de retirar, você ainda tem 7 dias para desistir. Veja a Política de Compras e Cancelamentos.' },
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
    </main>
    <BottomNav variante="publico" />
  </div>
</template>
