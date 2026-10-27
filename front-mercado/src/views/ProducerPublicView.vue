<script setup lang="ts">
/** Perfil público do produtor ("Nossa Jornada"). */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, assetUrl } from '@/services/api'
import { prefs } from '@/services/preferences'
import { toast } from '@/services/toast'
import { iniciais, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import ProductCard from '@/components/catalog/ProductCard.vue'
import BottomNav from '@/components/ui/BottomNav.vue'

const route = useRoute()
const router = useRouter()
const produtor = ref<any>(null)
const carregando = ref(true)
const seguindo = computed(() => produtor.value && prefs.isSeguindo(produtor.value.id))
const linkWhats = computed(() => {
  const d = (produtor.value?.whatsapp || '').replace(/\D/g, '')
  return d ? `https://wa.me/55${d}?text=${encodeURIComponent('Olá! Vi sua loja no Mercado Nativo.')}` : '#'
})

async function seguir() {
  const agora = prefs.alternarSeguir(produtor.value.id)
  try {
    const r = await api(`/api/v1/public/producers/${produtor.value.id}/seguir`, { method: 'POST', params: { seguir: agora } })
    produtor.value.seguidores = r.seguidores
  } catch { /* informativo */ }
}

onMounted(async () => {
  try {
    produtor.value = await api(`/api/v1/public/producers/${route.params.id}`)
  } catch (e) {
    toast.erro(e)
    router.replace('/')
  } finally {
    carregando.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <div v-if="carregando" class="h-72 bg-nativo animate-pulse" />
    <template v-else-if="produtor">
      <section class="bg-nativo text-white pt-8 pb-28 px-4 text-center">
        <RouterLink to="/" class="inline-flex items-center gap-1.5 text-sm text-white/90 hover:underline mb-6">
          <Icon name="arrow-left" class="w-4 h-4" /> Voltar à vitrine
        </RouterLink>
        <div class="w-24 h-24 mx-auto rounded-full bg-nativo-dark border-4 border-white/80 flex items-center justify-center text-2xl font-bold overflow-hidden">
          <img v-if="produtor.foto_perfil" :src="assetUrl(produtor.foto_perfil)" class="w-full h-full object-cover" alt="" />
          <span v-else>{{ iniciais(produtor.nome_loja) }}</span>
        </div>
        <h1 class="font-serif text-4xl font-bold mt-4">{{ produtor.nome_loja }}</h1>
        <p class="text-sm text-white/85 mt-2 flex items-center justify-center gap-1.5 flex-wrap">
          <Icon name="map-pin" class="w-4 h-4" /> Por {{ produtor.nome }} • {{ produtor.endereco ? `${produtor.endereco} - ` : '' }}{{ produtor.local }}
        </p>
        <button class="btn mt-5 rounded-full bg-white text-nativo px-6 py-2 text-sm" @click="seguir">
          <Icon name="bell" class="w-4 h-4" /> {{ seguindo ? 'Seguindo' : 'Seguir' }}
          <span v-if="produtor.seguidores" class="text-xs text-slate-500 font-normal">· {{ produtor.seguidores }}</span>
        </button>
      </section>

      <main class="max-w-5xl mx-auto px-4 -mt-20 pb-12 mb-nav">
        <div class="card p-6 sm:p-8 shadow-lg">
          <div class="flex items-center justify-between gap-3 mb-4">
            <h2 class="font-serif text-2xl font-bold text-slate-900">Nossa Jornada</h2>
            <span v-if="produtor.nota_media" class="flex items-center gap-1.5 text-sm font-semibold text-terra-dark bg-terra-light px-3 py-1.5 rounded-lg">
              <Icon name="star" filled class="w-4 h-4" /> {{ produtor.nota_media.toFixed(1) }}
              <span class="text-slate-600 font-medium">{{ produtor.nota_media >= 4.5 ? 'Top Produtor' : 'Avaliação' }}</span>
            </span>
          </div>
          <p class="italic text-slate-600 leading-relaxed whitespace-pre-line">{{ produtor.descricao || 'Produtor local do Mercado Nativo.' }}</p>

          <div class="grid sm:grid-cols-2 gap-4 mt-6">
            <a :href="linkWhats" target="_blank" rel="noopener" class="rounded-xl bg-slate-50 border border-slate-100 p-4 flex items-center gap-4 hover:border-nativo transition">
              <span class="w-10 h-10 rounded-full bg-nativo-light text-nativo flex items-center justify-center"><Icon name="phone" class="w-5 h-5" /></span>
              <span>
                <span class="block text-xs text-slate-500 font-semibold">Contato direto</span>
                <span class="font-bold text-slate-900">{{ telefone(produtor.whatsapp) }}</span>
              </span>
            </a>
            <div class="rounded-xl bg-slate-50 border border-slate-100 p-4 flex items-center gap-4">
              <span class="w-10 h-10 shrink-0 rounded-full bg-nativo-light text-nativo flex items-center justify-center"><Icon name="map-pin" class="w-5 h-5" /></span>
              <span class="min-w-0">
                <span class="block text-xs text-slate-500 font-semibold">Endereço para retirada</span>
                <span class="block font-bold text-slate-900 truncate">{{ produtor.endereco || 'Informado após o pedido' }}</span>
                <span class="block text-xs text-slate-600">{{ produtor.local }}{{ produtor.cep ? ` - CEP: ${produtor.cep}` : '' }}</span>
                <span class="inline-flex items-center gap-1 mt-1 text-xs font-semibold text-terra-dark bg-terra-button px-2 py-0.5 rounded">
                  <Icon name="clock" class="w-3 h-3" /> Agende um horário antes de ir
                </span>
              </span>
            </div>
          </div>
        </div>

        <h2 class="font-serif text-2xl font-bold text-slate-900 flex items-center gap-2 mt-10 mb-5">
          <Icon name="shopping-bag" class="w-6 h-6 text-nativo" /> Produtos desta propriedade
        </h2>
        <div v-if="produtor.produtos.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <ProductCard v-for="p in produtor.produtos" :key="p.id" :produto="p" :mostrar-produtor="false" />
        </div>
        <p v-else class="text-slate-600">Nenhum produto disponível no momento.</p>
      </main>
    </template>
    <BottomNav variante="publico" />
  </div>
</template>
