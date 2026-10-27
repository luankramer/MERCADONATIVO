<script setup lang="ts">
import { fecharToast, toasts } from '@/services/toast'
import Icon from './Icon.vue'
</script>

<template>
  <div class="fixed z-[60] top-4 inset-x-4 sm:inset-x-auto sm:right-4 sm:w-[26rem] space-y-2 pointer-events-none" aria-live="polite">
    <TransitionGroup enter-from-class="opacity-0 -translate-y-2" leave-to-class="opacity-0" enter-active-class="transition" leave-active-class="transition">
      <div v-for="t in toasts" :key="t.id" :role="t.tipo === 'erro' ? 'alert' : 'status'"
           :class="['pointer-events-auto flex items-start gap-3 rounded-2xl pl-4 pr-2 py-3 shadow-xl text-base font-medium border-2',
                    t.tipo === 'sucesso' ? 'bg-nativo text-white border-nativo-dark' :
                    t.tipo === 'erro' ? 'bg-white text-red-700 border-red-300' : 'bg-slate-900 text-white border-slate-800']">
        <Icon :name="t.tipo === 'sucesso' ? 'check-circle' : t.tipo === 'erro' ? 'alert' : 'bell'" class="w-6 h-6 shrink-0 mt-0.5" />
        <span class="flex-1 py-0.5">{{ t.texto }}</span>
        <button type="button" class="shrink-0 w-10 h-10 -my-1 rounded-xl flex items-center justify-center hover:bg-black/10" aria-label="Fechar aviso" @click="fecharToast(t.id)">
          <Icon name="x" class="w-5 h-5" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
