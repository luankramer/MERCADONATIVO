<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import Icon from '@/components/ui/Icon.vue'

const router = useRouter()
const email = ref('')
const password = ref('')
const isLoading = ref(false)

async function handleAdminLogin() {
  isLoading.value = true
  try {
    const data = await api('/api/v1/auth/admin/login', { method: 'POST', body: { email: email.value, senha: password.value } })
    session.loginAdmin(data)
    router.push('/admin/visao-geral')
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-12">
    <div class="w-full max-w-md card overflow-hidden">
      <div class="h-1.5 bg-slate-900" />
      <div class="p-8 sm:p-10">
        <RouterLink to="/" class="back-link mb-8"><Icon name="arrow-left" class="w-4 h-4" /> Voltar</RouterLink>
        <div class="flex flex-col items-center text-center mb-8">
          <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-5">
            <Icon name="shield" class="w-7 h-7 text-slate-800" />
          </div>
          <h1 class="font-serif text-3xl font-bold text-slate-900 mb-1">Painel Administrativo</h1>
          <p class="text-slate-500 text-sm">Acesso restrito para colaboradores.</p>
        </div>

        <form class="space-y-5" @submit.prevent="handleAdminLogin">
          <div>
            <label class="label">E-mail Institucional</label>
            <div class="relative">
              <Icon name="mail" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input v-model="email" type="email" placeholder="nome@mercadonativo.com" required autocomplete="username" class="input-soft pl-12 focus:border-slate-900 focus:ring-slate-200" />
            </div>
          </div>
          <div>
            <label class="label">Senha de Administrador</label>
            <div class="relative">
              <Icon name="key" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input v-model="password" type="password" placeholder="••••••••" required autocomplete="current-password" class="input pl-12 focus:border-slate-900 focus:ring-slate-200" />
            </div>
          </div>
          <button type="submit" :disabled="isLoading" class="btn-dark w-full py-4">
            <Icon v-if="isLoading" name="loader" class="w-5 h-5" /> {{ isLoading ? 'Autenticando...' : 'Acessar Painel' }}
          </button>
          <RouterLink to="/" class="block text-center text-sm text-slate-500 hover:text-slate-800">Não sou administrador</RouterLink>
        </form>
      </div>
    </div>
  </main>
</template>
