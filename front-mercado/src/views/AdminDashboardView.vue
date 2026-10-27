<script setup lang="ts">
/** Layout do painel administrativo (menu lateral + cabeçalho). As abas são rotas filhas. */
import { computed, onMounted, provide, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { iniciais } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

const route = useRoute()
const router = useRouter()
const menuAberto = ref(false)
const pendentes = ref(0)

const titulo = computed(() => (route.meta.titulo as string) || 'Painel')

async function atualizarPendentes() {
  try {
    const c = await api<Record<string, number>>('/api/v1/admin/products/counts', { auth: 'admin' })
    pendentes.value = c.pendente || 0
  } catch { /* sem bloqueio */ }
}
// As abas chamam isto após aprovar/rejeitar para atualizar o contador do menu
provide('atualizarPendentes', atualizarPendentes)
onMounted(atualizarPendentes)

const itens = [
  { to: '/admin/visao-geral', icone: 'grid', texto: 'Visão Geral' },
  { to: '/admin/aprovacoes', icone: 'image', texto: 'Aprovações', contador: true },
  { to: '/admin/vitrine-premium', icone: 'star', texto: 'Vitrine Premium' },
  { to: '/admin/vendedores', icone: 'user', texto: 'Vendedores' },
]

function logout() {
  session.logoutAdmin()
  router.push('/admin/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 lg:flex">
    <!-- Barra superior no celular -->
    <div class="lg:hidden flex items-center justify-between bg-painel-side text-white px-4 h-14">
      <span class="font-serif text-lg flex items-center gap-2"><Icon name="shield" class="w-5 h-5 text-emerald-500" /> Admin Nativo</span>
      <button class="p-2" aria-label="Menu" @click="menuAberto = !menuAberto"><Icon :name="menuAberto ? 'x' : 'grid'" class="w-5 h-5" /></button>
    </div>

    <aside :class="['bg-painel-side text-slate-300 flex-col justify-between w-full lg:w-64 lg:min-h-screen lg:flex lg:sticky lg:top-0 lg:h-screen', menuAberto ? 'flex' : 'hidden']">
      <div class="p-5">
        <div class="hidden lg:flex items-center gap-2 text-white font-serif text-xl mb-10 px-2 pt-2">
          <Icon name="shield" class="w-6 h-6 text-emerald-500" /> Admin Nativo
        </div>
        <nav class="space-y-1.5">
          <RouterLink v-for="item in itens" :key="item.to" :to="item.to" @click="menuAberto = false"
                      class="flex items-center gap-3 px-4 py-3 rounded-xl text-[15px] hover:bg-painel-item transition"
                      active-class="bg-painel-item text-white">
            <Icon :name="item.icone" class="w-5 h-5" /> {{ item.texto }}
            <span v-if="item.contador && pendentes" class="ml-auto text-xs font-bold text-amber-300 bg-amber-900/60 border border-amber-700 rounded-full px-2 py-0.5">{{ pendentes }}</span>
          </RouterLink>
          <p class="px-4 pt-6 pb-1 text-[11px] font-semibold uppercase tracking-widest text-slate-500">Sistema</p>
          <RouterLink to="/admin/administradores" @click="menuAberto = false"
                      class="flex items-center gap-3 px-4 py-3 rounded-xl text-[15px] hover:bg-painel-item transition" active-class="bg-painel-item text-white">
            <Icon name="shield" class="w-5 h-5" /> Administradores
          </RouterLink>
        </nav>
      </div>
      <button class="flex items-center gap-3 px-9 py-5 border-t border-white/10 text-[15px] hover:text-white text-left" @click="logout">
        <Icon name="log-out" class="w-5 h-5" /> Sair do Sistema
      </button>
    </aside>

    <div class="flex-1 min-w-0">
      <header class="bg-white border-b border-slate-200 px-6 sm:px-8 h-20 flex items-center justify-between gap-4">
        <h1 class="font-serif text-xl sm:text-2xl text-slate-900">{{ titulo }}</h1>
        <div class="flex items-center gap-3 text-sm text-slate-500">
          <span class="hidden sm:inline">{{ session.adminNome || 'Logado no Painel' }}</span>
          <span class="w-10 h-10 rounded-full bg-slate-900 text-white font-bold flex items-center justify-center">{{ iniciais(session.adminNome || 'AD') }}</span>
        </div>
      </header>
      <main class="p-4 sm:p-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>
