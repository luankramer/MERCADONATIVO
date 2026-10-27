<script setup lang="ts">
/** Dica para falar em vez de digitar: o microfone do teclado do celular já transforma voz em texto. */
import Icon from './Icon.vue'
</script>

<template>
  <p class="rounded-xl bg-nativo-soft border border-nativo-light p-3 text-slate-700 flex gap-3">
    <Icon name="mic" class="w-6 h-6 text-nativo shrink-0" />
    <span><strong>Prefere falar em vez de digitar?</strong> Toque no campo de texto e depois no <strong>microfone</strong> do teclado do celular.</span>
  </p>
</template>
