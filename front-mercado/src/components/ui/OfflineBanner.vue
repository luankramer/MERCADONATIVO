<script setup lang="ts">
/** Aviso claro quando a internet cai (comum na zona rural). Some sozinho quando volta. */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from './Icon.vue'

const offline = ref(typeof navigator !== 'undefined' && navigator.onLine === false)
const atualizar = () => (offline.value = !navigator.onLine)
onMounted(() => { window.addEventListener('online', atualizar); window.addEventListener('offline', atualizar) })
onBeforeUnmount(() => { window.removeEventListener('online', atualizar); window.removeEventListener('offline', atualizar) })
</script>

<template>
  <div v-if="offline" role="alert" class="fixed top-0 inset-x-0 z-[70] bg-slate-900 text-white px-4 py-3 pt-safe flex items-center justify-center gap-3 text-base font-semibold shadow-lg">
    <Icon name="wifi_off" class="w-6 h-6 shrink-0" />
    Sem internet no momento. Assim que a conexão voltar, é só tentar de novo.
  </div>
</template>
