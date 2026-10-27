<script setup lang="ts">
defineProps<{ modelValue: boolean; disabled?: boolean; rotulo?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()
</script>

<template>
  <button type="button" role="switch" :aria-checked="modelValue" :disabled="disabled"
          class="inline-flex items-center gap-2 disabled:opacity-40"
          @click="emit('update:modelValue', !modelValue)">
    <span v-if="rotulo" :class="['text-sm font-semibold', modelValue ? 'text-green-700' : 'text-slate-500']">
      {{ modelValue ? 'Ligado' : 'Desligado' }}
    </span>
    <span :class="['relative w-11 h-6 rounded-full border-2 transition', modelValue ? 'border-green-600 bg-green-50' : 'border-slate-300 bg-slate-100']">
      <span :class="['absolute top-0.5 w-4 h-4 rounded-full transition-all', modelValue ? 'left-[22px] bg-green-600' : 'left-0.5 bg-slate-400']" />
    </span>
  </button>
</template>
