<script setup lang="ts">
/** Estrelas de avaliação. Com v-model fica clicável; sem, apenas exibe. */
import Icon from './Icon.vue'

const props = withDefaults(defineProps<{ modelValue?: number; valor?: number; tamanho?: string; editavel?: boolean }>(), {
  tamanho: 'w-4 h-4',
  editavel: false,
})
const emit = defineEmits<{ 'update:modelValue': [number] }>()
const nota = () => props.modelValue ?? props.valor ?? 0
</script>

<template>
  <div class="flex items-center gap-1">
    <button v-for="i in 5" :key="i" type="button" :disabled="!editavel"
            :class="[editavel ? 'cursor-pointer hover:scale-110 transition' : 'cursor-default']"
            :aria-label="`${i} estrela${i > 1 ? 's' : ''}`" @click="emit('update:modelValue', i)">
      <Icon name="star" :filled="i <= Math.round(nota())" :stroke="1.5"
            :class="[tamanho, i <= Math.round(nota()) ? 'text-amber-400' : 'text-slate-300']" />
    </button>
  </div>
</template>
