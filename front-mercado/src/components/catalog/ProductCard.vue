<script setup lang="ts">
import { computed } from 'vue'
import { prefs } from '@/services/preferences'
import { moeda } from '@/utils/format'
import { NOME_CATEGORIA } from '@/utils/categorias'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'

export interface ProdutoCard {
  id: number
  nome: string
  preco: number
  categoria: string
  estoque: number
  imagem: string | null
  destaque: boolean
  nota_media: number | null
  total_avaliacoes: number
  distancia_km: number | null
  produtor: { id: number; nome_loja: string; cidade: string | null; estado: string; local: string } | null
}

const props = withDefaults(defineProps<{ produto: ProdutoCard; mostrarProdutor?: boolean }>(), { mostrarProdutor: true })

const esgotado = computed(() => props.produto.estoque <= 0)
const poucas = computed(() => !esgotado.value && props.produto.estoque <= 5)
const corCategoria = computed(() => {
  const c = props.produto.categoria
  if (esgotado.value) return 'bg-slate-100 text-slate-600'
  if (c === 'Hortifruti') return 'bg-slate-100 text-slate-700'
  return 'bg-terra-light text-terra-dark'
})
</script>

<template>
  <RouterLink :to="`/vitrine/produto/${produto.id}`"
              :class="['group block rounded-2xl bg-white p-3 transition hover:-translate-y-0.5 hover:shadow-lg',
                       produto.destaque ? 'border-2 border-destaque shadow-md shadow-terra-light' : 'border border-slate-200 shadow-sm']">
    <div class="relative aspect-[4/3] rounded-xl overflow-hidden border border-slate-100">
      <ImageBox :src="produto.imagem" :alt="produto.nome" />
      <span v-if="produto.destaque" class="absolute top-2 left-2 badge bg-destaque text-white shadow">
        <Icon name="star" filled class="w-4 h-4" /> Destaque
      </span>
      <button type="button" class="absolute top-1.5 right-1.5 w-12 h-12 rounded-full bg-white/95 shadow-md flex items-center justify-center"
              :aria-label="prefs.isFavorito(produto.id) ? `Tirar ${produto.nome} dos favoritos` : `Guardar ${produto.nome} nos favoritos`"
              :aria-pressed="prefs.isFavorito(produto.id)"
              @click.prevent.stop="prefs.alternarFavorito(produto.id)">
        <Icon name="heart" filled :class="['w-6 h-6', prefs.isFavorito(produto.id) ? 'text-red-500' : 'text-slate-400']" />
      </button>
      <div v-if="esgotado" class="absolute bottom-0 inset-x-0 bg-slate-800/90 text-white text-sm font-semibold py-2 flex items-center justify-center gap-1.5">
        <Icon name="package" class="w-4 h-4" /> Esgotado no momento
      </div>
      <div v-else-if="poucas" class="absolute bottom-0 inset-x-0 bg-terra text-white text-sm font-semibold py-2 flex items-center justify-center gap-1.5">
        <Icon name="clock" class="w-4 h-4" /> Restam só {{ produto.estoque }}
      </div>
    </div>
    <div class="px-1 pt-3 pb-1">
      <div class="flex items-center justify-between gap-2">
        <span :class="['badge', corCategoria]">{{ NOME_CATEGORIA[produto.categoria] || produto.categoria }}</span>
        <span v-if="produto.nota_media" class="flex items-center gap-1 text-sm font-semibold text-slate-700" :aria-label="`Nota ${produto.nota_media.toFixed(1)} de 5`">
          <Icon name="star" filled class="w-4 h-4 text-amber-500" /> {{ produto.nota_media.toFixed(1) }}
        </span>
      </div>
      <h3 class="font-serif text-xl font-bold text-slate-900 mt-2 leading-snug line-clamp-2">{{ produto.nome }}</h3>
      <p :class="['text-2xl font-bold mt-1', esgotado ? 'text-slate-500' : 'text-nativo']">{{ moeda(produto.preco) }}</p>
      <template v-if="mostrarProdutor && produto.produtor">
        <p class="text-base text-slate-700 mt-2 truncate">{{ produto.produtor.nome_loja }}</p>
        <p class="text-sm text-slate-600 flex items-center gap-1.5 mt-0.5">
          <Icon name="map-pin" class="w-4 h-4 shrink-0 text-nativo" />
          <span class="truncate">Retirada em {{ produto.produtor.local }}</span>
          <span v-if="produto.distancia_km !== null" class="shrink-0 font-semibold text-nativo">· {{ produto.distancia_km }} km</span>
        </p>
      </template>
    </div>
  </RouterLink>
</template>
