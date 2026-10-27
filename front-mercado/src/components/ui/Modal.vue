<script setup lang="ts">
/** Janela modal padrão. Uso: <Modal :aberto="x" titulo="..." @fechar="x=false"> conteúdo <template #rodape>...</template></Modal> */
import { onBeforeUnmount, watch } from 'vue'
import Icon from './Icon.vue'

const props = withDefaults(defineProps<{ aberto: boolean; titulo?: string; subtitulo?: string; largura?: string; icone?: string; tom?: 'padrao' | 'terra' }>(), {
  largura: 'max-w-lg',
  tom: 'padrao',
})
const emit = defineEmits<{ fechar: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.aberto) emit('fechar')
}
watch(() => props.aberto, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
}, { immediate: true })
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <Teleport to="body">
    <Transition enter-from-class="opacity-0" leave-to-class="opacity-0" enter-active-class="transition duration-150" leave-active-class="transition duration-150">
      <div v-if="aberto" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/60 backdrop-blur-[2px] p-0 sm:p-4" @click.self="emit('fechar')">
        <div :class="['w-full bg-white shadow-2xl rounded-t-3xl sm:rounded-3xl max-h-[92vh] flex flex-col', largura, tom === 'terra' ? 'ring-4 ring-terra-border/60' : '']">
          <header v-if="titulo" class="flex items-start justify-between gap-4 px-6 py-5 border-b border-slate-100">
            <div>
              <h2 :class="['font-serif text-2xl font-bold flex items-center gap-2', tom === 'terra' ? 'text-terra' : 'text-slate-900']">
                <Icon v-if="icone" :name="icone" class="w-5 h-5" /> {{ titulo }}
              </h2>
              <p v-if="subtitulo" class="text-sm font-medium text-terra mt-1 flex items-center gap-1">
                <Icon name="star" filled class="w-3 h-3" /> {{ subtitulo }}
              </p>
            </div>
            <button class="w-9 h-9 shrink-0 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-600" aria-label="Fechar" @click="emit('fechar')">
              <Icon name="x" class="w-6 h-6" />
            </button>
          </header>
          <div class="overflow-y-auto px-6 py-5 flex-1">
            <slot />
          </div>
          <footer v-if="$slots.rodape" class="px-6 py-4 bg-slate-50 border-t border-slate-100 rounded-b-3xl flex flex-wrap justify-end gap-3">
            <slot name="rodape" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
