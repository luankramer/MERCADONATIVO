<script setup lang="ts">
/** Barra de navegação inferior no celular (some a partir de tablets/desktop). */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { session } from '@/services/auth'
import Icon from './Icon.vue'

const props = defineProps<{ variante: 'publico' | 'produtor' }>()
const route = useRoute()

const itens = computed(() => props.variante === 'produtor'
  ? [
      { to: '/painel', icone: 'grid', texto: 'Painel' },
      { to: '/painel/produto/novo', icone: 'plus', texto: 'Anunciar' },
      { to: '/', icone: 'store', texto: 'Vitrine' },
      { to: '/painel/perfil', icone: 'user', texto: 'Perfil' },
    ]
  : [
      { to: '/', icone: 'home', texto: 'Início' },
      { to: '/?favoritos=1', icone: 'heart', texto: 'Favoritos' },
      { to: session.isProducer ? '/painel/produto/novo' : '/login-produtor', icone: 'camera', texto: 'Vender' },
      { to: session.isProducer ? '/painel' : '/login-produtor', icone: 'user', texto: session.isProducer ? 'Painel' : 'Entrar' },
    ])

function ativo(to: string) {
  const [caminho, query] = to.split('?')
  if (query) return route.path === caminho && route.fullPath.includes(query)
  return route.path === caminho && !route.fullPath.includes('favoritos=1')
}
</script>

<template>
  <nav class="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur border-t border-slate-200 pb-safe"
       aria-label="Navegação principal">
    <ul class="grid grid-cols-4">
      <li v-for="item in itens" :key="item.texto">
        <RouterLink :to="item.to" :aria-current="ativo(item.to) ? 'page' : undefined"
                    :class="['flex flex-col items-center justify-center gap-0.5 h-[4.5rem] text-sm font-semibold transition',
                             ativo(item.to) ? 'text-nativo' : 'text-slate-700']">
          <span :class="['w-14 h-8 rounded-full flex items-center justify-center transition', ativo(item.to) ? 'bg-nativo-light' : '']">
            <Icon :name="item.icone" :filled="item.icone === 'heart' && ativo(item.to)" class="w-6 h-6" />
          </span>
          {{ item.texto }}
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
