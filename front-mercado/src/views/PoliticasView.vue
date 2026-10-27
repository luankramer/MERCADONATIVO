<script setup lang="ts">
/** Políticas do site (textos em src/content/politicas.ts). Rota: /politicas/:slug */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'
import { moeda } from '@/utils/format'
import { ATUALIZADO_EM, EMPRESA, POLITICAS, VERSAO, politica } from '@/content/politicas'
import Icon from '@/components/ui/Icon.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import BottomNav from '@/components/ui/BottomNav.vue'

const route = useRoute()
const atual = computed(() => politica(String(route.params.slug || 'privacidade')) || POLITICAS[0]!)
const valores = ref({ comissao: 10, premium: 9.9 })

onMounted(async () => {
  try {
    const c = await api<{ percentual_plataforma: number; preco_premium: number }>('/api/v1/checkout/config')
    valores.value = { comissao: c.percentual_plataforma, premium: c.preco_premium }
  } catch { /* mantém os valores padrão */ }
})
watch(() => route.params.slug, () => window.scrollTo({ top: 0 }))

/** Troca {comissao}, {repasse} e {premium} e marca os [campos a preencher]. */
function partes(texto: string): { t: string; pendente: boolean }[] {
  const pronto = texto
    .replaceAll('{comissao}', String(valores.value.comissao).replace('.', ','))
    .replaceAll('{repasse}', String(100 - valores.value.comissao).replace('.', ','))
    .replaceAll('{premium}', moeda(valores.value.premium))
  return pronto.split(/(\[[^\]]+\])/g).filter(Boolean).map((t) => ({ t, pendente: /^\[.*\]$/.test(t) }))
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <PublicHeader />
    <main class="max-w-6xl mx-auto px-4 py-6 sm:py-10 mb-nav flex flex-col lg:grid lg:grid-cols-[17rem_1fr] lg:gap-8">
      <!-- Lista das políticas -->
      <!-- No celular o texto vem primeiro e a lista das outras políticas fica no fim -->
      <nav aria-label="Políticas" class="order-2 lg:order-none mt-6 lg:mt-0">
        <p class="text-lg font-bold text-slate-900 mb-3"><span class="lg:hidden">Outras políticas</span><span class="hidden lg:inline">Políticas do {{ EMPRESA.nome }}</span></p>
        <ul class="grid sm:grid-cols-2 lg:grid-cols-1 gap-2">
          <li v-for="p in POLITICAS" :key="p.slug">
            <RouterLink :to="`/politicas/${p.slug}`" :aria-current="p.slug === atual.slug ? 'page' : undefined"
                        :class="['flex items-center gap-3 rounded-xl border-2 px-4 py-3 font-semibold transition min-h-[56px]',
                                 p.slug === atual.slug ? 'border-nativo bg-nativo-light text-nativo' : 'border-slate-200 bg-white text-slate-700 hover:border-nativo']">
              <Icon :name="p.icone" class="w-5 h-5 shrink-0" /> {{ p.titulo }}
            </RouterLink>
          </li>
        </ul>
      </nav>

      <article class="order-1 lg:order-none card p-6 sm:p-10 min-w-0">
        <h1 class="font-serif text-3xl sm:text-4xl font-bold text-slate-900">{{ atual.titulo }}</h1>
        <p class="text-slate-600 mt-2">Versão {{ VERSAO }} · atualizada em {{ ATUALIZADO_EM }}</p>

        <section class="mt-6 rounded-2xl bg-nativo-soft border border-nativo-light p-5" aria-labelledby="resumo">
          <h2 id="resumo" class="text-lg font-bold text-nativo flex items-center gap-2"><Icon name="check-circle" class="w-6 h-6" /> Resumo em poucas palavras</h2>
          <ul class="mt-3 space-y-2">
            <li v-for="r in atual.resumo" :key="r" class="flex gap-2 text-slate-800"><span class="text-nativo font-bold">✓</span> <span>{{ r }}</span></li>
          </ul>
        </section>

        <section v-for="s in atual.secoes" :key="s.titulo" class="mt-8">
          <h2 class="text-xl font-bold text-slate-900">{{ s.titulo }}</h2>
          <p v-for="(t, i) in s.texto || []" :key="'t' + i" class="mt-3 text-slate-700 leading-relaxed">
            <template v-for="(pt, j) in partes(t)" :key="j"><mark v-if="pt.pendente" class="bg-amber-100 text-amber-900 rounded px-1">{{ pt.t }}</mark><template v-else>{{ pt.t }}</template></template>
          </p>
          <ul v-if="s.itens" class="mt-3 space-y-2.5">
            <li v-for="(it, i) in s.itens" :key="'i' + i" class="flex gap-3 text-slate-700 leading-relaxed">
              <span class="mt-2.5 w-2 h-2 shrink-0 rounded-full bg-nativo" aria-hidden="true" />
              <span><template v-for="(pt, j) in partes(it)" :key="j"><mark v-if="pt.pendente" class="bg-amber-100 text-amber-900 rounded px-1">{{ pt.t }}</mark><template v-else>{{ pt.t }}</template></template></span>
            </li>
          </ul>
        </section>

        <p class="mt-10 pt-6 border-t border-slate-100 text-sm text-slate-600">
          Ficou com dúvida? Veja a página <RouterLink to="/ajuda" class="text-nativo font-semibold underline">Ajuda</RouterLink>.
        </p>
      </article>
    </main>
    <BottomNav variante="publico" />
  </div>
</template>
