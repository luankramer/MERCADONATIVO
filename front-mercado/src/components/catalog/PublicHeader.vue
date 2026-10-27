<script setup lang="ts">
import { useRouter } from 'vue-router'
import { session } from '@/services/auth'
import Icon from '@/components/ui/Icon.vue'
import FontSizeControl from '@/components/ui/FontSizeControl.vue'

const router = useRouter()
function anunciar() {
  router.push(session.isProducer ? '/painel/produto/novo' : '/login-produtor')
}
</script>

<template>
  <header class="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200">
    <div class="max-w-6xl mx-auto px-4 h-16 sm:h-20 flex items-center justify-between gap-3">
      <RouterLink to="/" class="flex items-center shrink min-w-0" aria-label="Mercado Nativo, página inicial">
        <img src="/logo-cabecalho.svg" alt="Mercado Nativo" class="h-9 sm:h-11 w-auto max-w-full" width="244" height="44" />
      </RouterLink>
      <nav class="flex items-center gap-2 sm:gap-3 shrink-0" aria-label="Atalhos">
        <RouterLink to="/ajuda" class="flex items-center gap-1.5 rounded-xl px-2.5 sm:px-3 min-h-[44px] font-semibold border border-slate-200 bg-white text-slate-700 hover:border-nativo">
          <Icon name="help" class="w-5 h-5 text-nativo" /> Ajuda
        </RouterLink>
        <FontSizeControl />
        <!-- No celular "Vender" e "Entrar" ficam no menu de baixo, sempre com nome -->
        <button class="hidden md:flex items-center gap-2 font-semibold text-terra hover:underline px-3 min-h-[44px]" @click="anunciar">
          <Icon name="camera" class="w-5 h-5" /> Anunciar produto
        </button>
        <RouterLink :to="session.isProducer ? '/painel' : '/login-produtor'"
                    class="hidden md:flex items-center gap-2 font-semibold text-nativo hover:underline px-3 min-h-[44px]">
          <Icon name="user" class="w-5 h-5" /> {{ session.isProducer ? 'Meu painel' : 'Sou produtor' }}
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
