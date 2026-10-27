<script setup lang="ts">
/** Botão "Aa": a pessoa escolhe o tamanho da letra do site (fica guardado neste aparelho). */
import { onBeforeUnmount, ref } from 'vue'
import { prefs, type TamanhoLetra } from '@/services/preferences'

withDefaults(defineProps<{ escuro?: boolean }>(), { escuro: false })
const aberto = ref(false)
const raiz = ref<HTMLElement | null>(null)
const OPCOES: { valor: TamanhoLetra; texto: string; classe: string }[] = [
  { valor: 'normal', texto: 'Normal', classe: 'text-base' },
  { valor: 'grande', texto: 'Grande', classe: 'text-lg' },
  { valor: 'maior', texto: 'Maior', classe: 'text-xl' },
]

function fora(e: MouseEvent) {
  if (raiz.value && !raiz.value.contains(e.target as Node)) aberto.value = false
}
function alternar() {
  aberto.value = !aberto.value
  if (aberto.value) setTimeout(() => document.addEventListener('click', fora))
  else document.removeEventListener('click', fora)
}
function escolher(v: TamanhoLetra) {
  prefs.mudarLetra(v)
  aberto.value = false
  document.removeEventListener('click', fora)
}
onBeforeUnmount(() => document.removeEventListener('click', fora))
</script>

<template>
  <div ref="raiz" class="relative">
    <button type="button" :aria-expanded="aberto" aria-label="Tamanho da letra"
            :class="['flex items-center gap-1.5 rounded-xl px-2.5 sm:px-3 min-h-[44px] min-w-[44px] justify-center font-semibold border transition',
                     escuro ? 'border-white/30 text-white hover:bg-white/10' : 'border-slate-200 text-slate-700 bg-white hover:border-nativo']"
            @click="alternar">
      <span class="font-serif text-lg leading-none">A<span class="text-sm">a</span></span>
      <span class="text-sm hidden sm:inline">Letra</span>
    </button>
    <div v-if="aberto" class="absolute right-0 mt-2 w-56 rounded-2xl bg-white shadow-xl border border-slate-200 p-2 z-50 text-slate-800">
      <p class="px-3 pt-1 pb-2 text-sm font-semibold text-slate-600">Tamanho da letra</p>
      <button v-for="o in OPCOES" :key="o.valor" type="button"
              :class="['w-full flex items-center justify-between rounded-xl px-3 py-3 font-semibold', o.classe,
                       prefs.letra === o.valor ? 'bg-nativo-light text-nativo' : 'hover:bg-slate-50']"
              @click="escolher(o.valor)">
        {{ o.texto }}
        <span v-if="prefs.letra === o.valor" class="text-sm">✓ em uso</span>
      </button>
    </div>
  </div>
</template>
