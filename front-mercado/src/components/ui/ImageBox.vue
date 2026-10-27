<script setup lang="ts">
/** Imagem do produto com placeholder quando não houver foto. */
import { ref, watch } from 'vue'
import { assetUrl } from '@/services/api'
import Icon from './Icon.vue'

const props = defineProps<{ src?: string | null; alt?: string; iconClass?: string }>()
const falhou = ref(false)
watch(() => props.src, () => (falhou.value = false))
</script>

<template>
  <img v-if="src && !falhou" :src="assetUrl(src)" :alt="alt || ''" class="w-full h-full object-cover" loading="lazy" @error="falhou = true" />
  <div v-else class="w-full h-full flex items-center justify-center bg-slate-100">
    <Icon name="image" :class="iconClass || 'w-12 h-12 text-slate-300'" :stroke="1.5" />
  </div>
</template>
