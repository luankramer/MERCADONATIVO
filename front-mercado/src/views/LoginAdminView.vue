<script setup lang="ts">
/**
 * Login do painel administrativo, com "Esqueci minha senha":
 * e-mail -> código de 6 números (WhatsApp e/ou e-mail cadastrados) -> senha nova.
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import Icon from '@/components/ui/Icon.vue'

type Etapa = 'login' | 'pedir' | 'codigo'

const router = useRouter()
const etapa = ref<Etapa>('login')
const email = ref('')
const password = ref('')
const isLoading = ref(false)

// Recuperação
const desafio = ref('')
const avisoEnvio = ref('')
const codigo = ref('')
const novaSenha = ref('')
const repetirSenha = ref('')

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

function abrirRecuperacao() {
  etapa.value = 'pedir'
  codigo.value = ''
  novaSenha.value = ''
  repetirSenha.value = ''
}

async function pedirCodigo() {
  isLoading.value = true
  try {
    const r = await api<{ desafio: string; mensagem: string }>('/api/v1/auth/admin/recuperar', {
      method: 'POST', body: { email: email.value },
    })
    desafio.value = r.desafio
    avisoEnvio.value = r.mensagem
    etapa.value = 'codigo'
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}

async function redefinirSenha() {
  if (novaSenha.value !== repetirSenha.value) {
    toast.erro('As duas senhas não são iguais.')
    return
  }
  isLoading.value = true
  try {
    await api('/api/v1/auth/admin/recuperar/confirmar', {
      method: 'POST', body: { desafio: desafio.value, codigo: codigo.value.replace(/\D/g, ''), nova_senha: novaSenha.value },
    })
    toast.sucesso('Senha alterada! Entre com a nova senha.')
    password.value = ''
    etapa.value = 'login'
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}

function voltarAoLogin() {
  etapa.value = 'login'
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-12">
    <div class="w-full max-w-md card overflow-hidden">
      <div class="h-1.5 bg-slate-900" />
      <div class="p-8 sm:p-10">
        <RouterLink v-if="etapa === 'login'" to="/" class="back-link mb-8"><Icon name="arrow-left" class="w-4 h-4" /> Voltar</RouterLink>
        <button v-else type="button" class="back-link mb-8" @click="voltarAoLogin"><Icon name="arrow-left" class="w-4 h-4" /> Voltar para o login</button>

        <div class="flex flex-col items-center text-center mb-8">
          <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-5">
            <Icon :name="etapa === 'login' ? 'shield' : 'key'" class="w-7 h-7 text-slate-800" />
          </div>
          <h1 class="font-serif text-3xl font-bold text-slate-900 mb-1">
            {{ etapa === 'login' ? 'Painel Administrativo' : 'Recuperar acesso' }}
          </h1>
          <p class="text-slate-500 text-sm">
            <template v-if="etapa === 'login'">Acesso restrito para colaboradores.</template>
            <template v-else-if="etapa === 'pedir'">Informe o seu e-mail de administrador. Vamos mandar um código de 6 números.</template>
            <template v-else>Digite o código que chegou e escolha uma senha nova.</template>
          </p>
        </div>

        <!-- 1. Login -->
        <form v-if="etapa === 'login'" class="space-y-5" @submit.prevent="handleAdminLogin">
          <div>
            <label class="label" for="adm-email">E-mail Institucional</label>
            <div class="relative">
              <Icon name="mail" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input id="adm-email" v-model="email" type="email" placeholder="nome@mercadonativo.com" required autocomplete="username" class="input-soft pl-12 focus:border-slate-900 focus:ring-slate-200" />
            </div>
          </div>
          <div>
            <label class="label" for="adm-senha">Senha de Administrador</label>
            <div class="relative">
              <Icon name="key" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input id="adm-senha" v-model="password" type="password" placeholder="••••••••" required autocomplete="current-password" class="input pl-12 focus:border-slate-900 focus:ring-slate-200" />
            </div>
          </div>
          <button type="submit" :disabled="isLoading" class="btn-dark w-full py-4">
            <Icon v-if="isLoading" name="loader" class="w-5 h-5" /> {{ isLoading ? 'Autenticando...' : 'Acessar Painel' }}
          </button>
          <button type="button" class="block w-full text-center text-sm font-semibold text-slate-700 underline underline-offset-4 hover:text-slate-900" @click="abrirRecuperacao">
            Esqueci minha senha
          </button>
          <RouterLink to="/" class="block text-center text-sm text-slate-500 hover:text-slate-800">Não sou administrador</RouterLink>
        </form>

        <!-- 2. Pedir o código -->
        <form v-else-if="etapa === 'pedir'" class="space-y-5" @submit.prevent="pedirCodigo">
          <div>
            <label class="label" for="rec-email">E-mail de administrador</label>
            <div class="relative">
              <Icon name="mail" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input id="rec-email" v-model="email" type="email" placeholder="nome@mercadonativo.com" required autocomplete="username" class="input-soft pl-12 focus:border-slate-900 focus:ring-slate-200" />
            </div>
          </div>
          <button type="submit" :disabled="isLoading" class="btn-dark w-full py-4">
            <Icon :name="isLoading ? 'loader' : 'message'" class="w-5 h-5" /> {{ isLoading ? 'Enviando...' : 'Enviar código' }}
          </button>
          <p class="text-xs text-slate-500 text-center">
            O código vai para o WhatsApp e para o e-mail cadastrados. Sem WhatsApp no cadastro? Peça ao Super Admin para trocar a sua senha.
          </p>
        </form>

        <!-- 3. Código + senha nova -->
        <form v-else class="space-y-5" @submit.prevent="redefinirSenha">
          <p class="rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm p-4" role="status">{{ avisoEnvio }}</p>
          <div>
            <label class="label" for="rec-codigo">Código de 6 números</label>
            <input id="rec-codigo" v-model="codigo" inputmode="numeric" autocomplete="one-time-code" maxlength="7" required pattern="\d{3}\s?\d{3}" placeholder="000000" class="input text-center text-2xl tracking-[0.4em] font-semibold" />
          </div>
          <div>
            <label class="label" for="rec-senha">Senha nova</label>
            <input id="rec-senha" v-model="novaSenha" type="password" required minlength="8" autocomplete="new-password" class="input" placeholder="Pelo menos 8 caracteres" />
          </div>
          <div>
            <label class="label" for="rec-senha2">Repita a senha nova</label>
            <input id="rec-senha2" v-model="repetirSenha" type="password" required minlength="8" autocomplete="new-password" class="input" />
          </div>
          <button type="submit" :disabled="isLoading" class="btn-dark w-full py-4">
            <Icon :name="isLoading ? 'loader' : 'check'" class="w-5 h-5" /> {{ isLoading ? 'Salvando...' : 'Salvar senha nova' }}
          </button>
          <button type="button" class="block w-full text-center text-sm text-slate-600 underline underline-offset-4 hover:text-slate-900" :disabled="isLoading" @click="pedirCodigo">
            Não chegou? Enviar outro código
          </button>
        </form>
      </div>
    </div>
  </main>
</template>
