<script setup lang="ts">
/** "Passo 2 de 3": mostra em que parte da compra a pessoa está. */
withDefaults(defineProps<{ atual: number; passos?: string[] }>(), {
  passos: () => ['Seus dados', 'Pagamento', 'Retirada'],
})
</script>

<template>
  <nav aria-label="Etapas da compra" class="mb-5">
    <p class="text-base font-semibold text-slate-800 mb-2">Passo {{ atual }} de {{ passos.length }}: {{ passos[atual - 1] }}</p>
    <ol class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${passos.length}, minmax(0, 1fr))` }">
      <li v-for="(p, i) in passos" :key="p" :aria-current="i + 1 === atual ? 'step' : undefined">
        <span :class="['block h-2.5 rounded-full', i + 1 <= atual ? 'bg-nativo' : 'bg-slate-200']" />
        <span :class="['block text-sm mt-1 truncate', i + 1 === atual ? 'text-nativo font-semibold' : 'text-slate-600']">{{ i + 1 }}. {{ p }}</span>
      </li>
    </ol>
  </nav>
</template>
