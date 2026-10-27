<script setup lang="ts">
/** Vitrine principal do consumidor (Figura 2 do TCC). */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { prefs } from '@/services/preferences'
import { CATEGORIAS as CATEGORIAS_PRODUTO, ICONE_CATEGORIA, NOME_CATEGORIA } from '@/utils/categorias'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import Icon from '@/components/ui/Icon.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import ProductCard, { type ProdutoCard } from '@/components/catalog/ProductCard.vue'
import FilterModal, { type FiltrosGeo } from '@/components/catalog/FilterModal.vue'
import BottomNav from '@/components/ui/BottomNav.vue'
import { watch } from 'vue'

const route = useRoute()
const router = useRouter()

const RAIO_MAX = 200
// Desenho + nome em cada categoria: ajuda quem lê com dificuldade (lista única em utils/categorias.ts)
const CATEGORIAS = ['Todos', ...CATEGORIAS_PRODUTO]

const produtos = ref<ProdutoCard[]>([])
const carregando = ref(true)
const modalFiltros = ref(false)
const somenteFavoritos = ref(route.query.favoritos === '1')
watch(() => route.query.favoritos, (v) => { somenteFavoritos.value = v === '1' })
const categoria = ref((route.query.categoria as string) || 'Todos')
const filtros = reactive<FiltrosGeo>({
  estado: (route.query.estado as string) || 'AC',
  cidade: (route.query.cidade as string) || '',
  raio: Number(route.query.raio) || RAIO_MAX,
  lat: null,
  lng: null,
  q: (route.query.q as string) || '',
})

const rotuloLocal = computed(() => {
  const raio = filtros.raio < RAIO_MAX ? ` (até ${filtros.raio} km)` : ''
  if (filtros.lat !== null) return `Perto de você${raio}`
  if (filtros.cidade) return `${filtros.cidade}, ${filtros.estado}${raio}`
  return `Todo o estado do ${filtros.estado}`
})

const visiveis = computed(() => somenteFavoritos.value ? produtos.value.filter((p) => prefs.isFavorito(p.id)) : produtos.value)

async function carregar() {
  carregando.value = true
  const usarRaio = (filtros.cidade || filtros.lat !== null) && filtros.raio < RAIO_MAX
  try {
    produtos.value = await api<ProdutoCard[]>('/api/v1/public/products', {
      params: {
        categoria: categoria.value,
        estado: filtros.estado,
        cidade: filtros.cidade,
        raio_km: usarRaio ? filtros.raio : filtros.cidade ? RAIO_MAX : undefined,
        lat: filtros.lat,
        lng: filtros.lng,
        q: filtros.q,
      },
    })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
  router.replace({ query: {
    ...(categoria.value !== 'Todos' ? { categoria: categoria.value } : {}),
    ...(filtros.cidade ? { cidade: filtros.cidade, raio: String(filtros.raio) } : {}),
    ...(filtros.estado !== 'AC' ? { estado: filtros.estado } : {}),
    ...(filtros.q ? { q: filtros.q } : {}),
    ...(somenteFavoritos.value ? { favoritos: '1' } : {}),
  } })
}

const termoBusca = ref(filtros.q)
watch(() => filtros.q, (v) => { termoBusca.value = v })

function buscar() {
  filtros.q = termoBusca.value.trim()
  ;(document.activeElement as HTMLElement | null)?.blur() // fecha o teclado no celular
  carregar()
}

function escolherCategoria(c: string) {
  categoria.value = c
  carregar()
}

function aplicarFiltros(novos: FiltrosGeo) {
  Object.assign(filtros, novos)
  modalFiltros.value = false
  carregar()
}

onMounted(carregar)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <PublicHeader />
    <main class="max-w-6xl mx-auto px-4 py-5 sm:py-6 mb-nav">
      <!-- Abertura: mensagem curta + busca + local, tudo no mesmo bloco -->
      <section class="relative overflow-hidden rounded-3xl bg-nativo text-white px-5 py-5 sm:px-10 sm:py-10 mb-5 sm:mb-6">
        <img src="/logo-simbolo-branco.svg" alt="" aria-hidden="true"
             class="hidden md:block absolute right-8 lg:right-16 top-1/2 -translate-y-1/2 w-56 lg:w-72 opacity-10 pointer-events-none select-none" />
        <div class="relative max-w-3xl">
          <h1 class="font-serif text-[1.6rem] sm:text-4xl font-bold leading-tight">Compre direto de quem produz na sua região</h1>
          <p class="hidden sm:block mt-2 text-lg text-nativo-light">Alimentos, hortaliças e artesanato vendidos por quem fez.</p>

          <form class="mt-4 sm:mt-6 flex gap-2" role="search" @submit.prevent="buscar">
            <label for="busca" class="sr-only">Buscar produtos</label>
            <div class="relative flex-1">
              <Icon name="search" class="w-5 h-5 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input id="busca" v-model="termoBusca" type="search" enterkeyhint="search" autocomplete="off"
                     class="input h-14 pl-12 pr-4 text-base rounded-2xl border-0 text-slate-900" placeholder="Buscar produto" />
            </div>
            <button type="submit" class="btn h-14 rounded-2xl px-5 sm:px-8 text-base bg-terra text-white hover:bg-terra-dark">
              <span class="hidden sm:inline">Buscar</span><Icon name="search" class="w-5 h-5 sm:hidden" />
            </button>
          </form>

          <div class="mt-3 sm:mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-base">
            <button class="flex items-center gap-1.5 min-w-0 py-1" @click="modalFiltros = true">
              <Icon name="map-pin" class="w-5 h-5 shrink-0" />
              <span class="text-nativo-light shrink-0">Mostrando:</span>
              <span class="font-semibold underline underline-offset-4 truncate">{{ rotuloLocal }}</span>
            </button>
            <button class="hidden sm:inline font-semibold underline underline-offset-4 py-1" @click="modalFiltros = true">Trocar cidade</button>
          </div>
        </div>
      </section>

      <div class="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 mb-4 scrollbar-none">
        <button v-for="c in CATEGORIAS" :key="c"
                :class="['shrink-0 pl-3 pr-5 py-2 rounded-full text-base font-semibold border-2 transition flex items-center gap-2 min-h-[52px]',
                         categoria === c ? 'bg-nativo text-white border-nativo' : 'bg-white text-slate-700 border-slate-200 hover:border-nativo']"
                :aria-pressed="categoria === c"
                @click="escolherCategoria(c)">
          <span :class="['w-9 h-9 rounded-full flex items-center justify-center', categoria === c ? 'bg-white/20' : 'bg-nativo-light text-nativo']">
            <Icon :name="ICONE_CATEGORIA[c] || 'grid'" class="w-5 h-5" />
          </span>
          {{ NOME_CATEGORIA[c] || c }}
        </button>
        <button :aria-pressed="somenteFavoritos" :class="['shrink-0 px-5 py-2 rounded-full text-base font-semibold border-2 flex items-center gap-2 transition min-h-[52px]',
                         somenteFavoritos ? 'bg-red-50 text-red-700 border-red-200' : 'bg-white text-slate-700 border-slate-200']"
                @click="somenteFavoritos = !somenteFavoritos; router.replace({ query: { ...route.query, favoritos: somenteFavoritos ? '1' : undefined } })">
          <Icon name="heart" :filled="somenteFavoritos" class="w-5 h-5" /> Meus favoritos
        </button>
      </div>

      <p v-if="filtros.q" class="text-sm text-slate-600 mb-4">
        Resultados para "<strong>{{ filtros.q }}</strong>"
        <button class="text-nativo underline ml-1 p-1" @click="termoBusca = ''; filtros.q = ''; carregar()">limpar busca</button>
      </p>

      <div v-if="carregando" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 6" :key="i" class="h-80 rounded-2xl bg-white border border-slate-100 animate-pulse" />
      </div>
      <div v-else-if="visiveis.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <ProductCard v-for="p in visiveis" :key="p.id" :produto="p" />
      </div>
      <div v-else class="card p-10 text-center">
        <Icon name="search" class="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <p class="font-serif text-xl font-bold text-slate-800">{{ somenteFavoritos ? 'Você ainda não favoritou nada' : 'Nada por aqui ainda' }}</p>
        <p class="text-sm text-slate-600 mt-1">{{ somenteFavoritos ? 'Toque no coração dos produtos que você gostar.' : 'Tente outra categoria ou aumente a distância.' }}</p>
        <button class="btn-outline mt-5" @click="modalFiltros = true">Ajustar filtros</button>
      </div>

      <!-- Convite para quem produz -->
      <section class="mt-10 rounded-2xl bg-terra-light border border-terra-border p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h2 class="font-serif text-xl sm:text-2xl font-bold text-terra">Você planta, cria ou cozinha?</h2>
          <p class="text-slate-700 mt-1">Anuncie seus produtos e receba os pedidos pelo WhatsApp.</p>
        </div>
        <RouterLink :to="session.isProducer ? '/painel/produto/novo' : '/login-produtor'"
                    class="btn rounded-full px-7 py-3.5 bg-terra text-white hover:brightness-110 text-base shrink-0">
          <Icon name="camera" class="w-5 h-5" /> Quero vender
        </RouterLink>
      </section>

      <nav aria-label="Políticas" class="mt-10 pt-6 border-t border-slate-200 flex flex-wrap gap-x-6 gap-y-2 text-base">
        <RouterLink to="/politicas/privacidade" class="text-slate-700 underline underline-offset-4 py-1">Privacidade</RouterLink>
        <RouterLink to="/politicas/termos" class="text-slate-700 underline underline-offset-4 py-1">Termos de Uso</RouterLink>
        <RouterLink to="/politicas/compras" class="text-slate-700 underline underline-offset-4 py-1">Compras e cancelamentos</RouterLink>
        <RouterLink to="/politicas/vendedores" class="text-slate-700 underline underline-offset-4 py-1">Regras para vendedores</RouterLink>
        <RouterLink to="/politicas/cookies" class="text-slate-700 underline underline-offset-4 py-1">Cookies</RouterLink>
      </nav>
      <footer class="mt-4 pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
        <span class="flex items-center gap-1.5"><img src="/logo-simbolo.svg" alt="" class="w-5 h-auto" width="20" height="18" /> Mercado Nativo · "Onde a cultura encontra o consumo consciente."</span>
        <RouterLink to="/ajuda" class="flex items-center gap-1.5 p-2 font-semibold text-nativo hover:underline">
          <Icon name="help" class="w-5 h-5" /> Ajuda: como comprar e vender
        </RouterLink>
        <RouterLink to="/admin/login" class="flex items-center gap-1.5 p-2 hover:text-slate-800">
          <Icon name="shield" class="w-4 h-4" /> Acesso restrito
        </RouterLink>
      </footer>
    </main>

    <BottomNav variante="publico" />
    <FilterModal :aberto="modalFiltros" :filtros="filtros" :raio-maximo="RAIO_MAX" @fechar="modalFiltros = false" @aplicar="aplicarFiltros" />
  </div>
</template>
