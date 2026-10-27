<script setup lang="ts">
/** Login simplificado do produtor: código de acesso enviado pelo WhatsApp (sem senha). */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import { mascaraTelefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import FontSizeControl from '@/components/ui/FontSizeControl.vue'

const router = useRouter()
const route = useRoute()
const whatsapp = ref('')
const code = ref('')
const step = ref(1)
const isLoading = ref(false)
const avisoTerminal = ref(false)
// Se já existir uma sessão válida, oferece ir ao painel (sem pular a tela de login)
const jaConectado = ref(session.isProducer)

function entrarComOutroNumero() {
  session.logoutProducer()
  jaConectado.value = false
}

async function handleRequestCode() {
  isLoading.value = true
  try {
    const r = await api<{ enviado: boolean }>('/api/v1/auth/producer/request-code', {
      method: 'POST', body: { whatsapp: whatsapp.value },
    })
    avisoTerminal.value = !r.enviado
    step.value = 2
    if (r.enviado) toast.sucesso('Enviamos o código para o seu WhatsApp.')
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}

async function handleVerifyCode() {
  isLoading.value = true
  try {
    const data = await api<{ access_token: string }>('/api/v1/auth/producer/verify-code', {
      method: 'POST', body: { whatsapp: whatsapp.value, code: code.value },
    })
    session.loginProducer(data.access_token)
    router.push((route.query.voltar as string) || '/painel')
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 flex items-center justify-center p-4 sm:p-12">
    <div class="w-full max-w-md card p-8 sm:p-10">
      <div class="flex items-center justify-between gap-3 mb-6">
        <button class="back-link" @click="step === 2 ? (step = 1, code = '') : router.push('/')">
          <Icon name="arrow-left" class="w-5 h-5" /> Voltar
        </button>
        <FontSizeControl />
      </div>

      <div class="flex flex-col items-center text-center mb-8">
        <img src="/logo-simbolo.svg" alt="" class="w-20 h-auto mb-5" width="80" height="73" />
        <h1 class="font-serif text-3xl font-bold text-slate-900 mb-1">Acesse sua conta</h1>
        <p class="text-slate-600 text-sm">Bem-vindo de volta ao Mercado Nativo.</p>
      </div>

      <div v-if="jaConectado" class="space-y-3">
        <div class="rounded-xl bg-nativo-soft border border-nativo-light p-4 text-center text-sm text-nativo">
          Você já está conectado neste navegador.
        </div>
        <button class="btn-primary w-full py-4" @click="router.push('/painel')">Ir para o meu painel</button>
        <button class="btn-ghost w-full" @click="entrarComOutroNumero">Entrar com outro número</button>
      </div>

      <form v-else-if="step === 1" class="space-y-5" @submit.prevent="handleRequestCode">
        <div>
          <label class="label">Número do WhatsApp</label>
          <div class="relative">
            <Icon name="message" class="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
            <input :value="whatsapp" type="tel" inputmode="tel" placeholder="(68) 9 9999-9999" required class="input pl-12"
                   @input="whatsapp = mascaraTelefone(($event.target as HTMLInputElement).value)" />
          </div>
          <p class="text-xs text-slate-500 mt-2">Sem senha: você recebe um código no WhatsApp.</p>
        </div>
        <button type="submit" :disabled="isLoading" class="btn-primary w-full py-4">
          <Icon v-if="isLoading" name="loader" class="w-5 h-5" /> {{ isLoading ? 'Enviando...' : 'Continuar' }}
        </button>
      </form>

      <form v-else class="space-y-5" @submit.prevent="handleVerifyCode">
        <div class="rounded-xl bg-nativo-soft border border-nativo-light p-4 text-center text-sm text-nativo">
          Enviamos um código de 6 dígitos para<br /><strong class="tracking-wide">{{ whatsapp }}</strong>
        </div>
        <div v-if="avisoTerminal" class="rounded-xl bg-amber-50 border border-amber-200 p-3 text-center text-sm text-amber-800">
          O WhatsApp está fora do ar agora. Em modo de desenvolvimento, o código aparece na janela do backend.
        </div>
        <div>
          <label class="label text-center">Código de Acesso</label>
          <input v-model="code" type="text" inputmode="numeric" autocomplete="one-time-code" placeholder="000000" required maxlength="6"
                 class="input text-2xl tracking-[0.5em] text-center font-bold" />
        </div>
        <button type="submit" :disabled="isLoading || code.length < 6" class="btn-primary w-full py-4">
          <Icon v-if="isLoading" name="loader" class="w-5 h-5" /> {{ isLoading ? 'Verificando...' : 'Acessar Conta' }}
        </button>
        <button type="button" class="w-full text-sm text-nativo hover:underline" :disabled="isLoading" @click="handleRequestCode">Reenviar código</button>
      </form>

      <div class="mt-8 text-center border-t border-slate-100 pt-6">
        <p class="text-sm text-slate-600 mb-1">Ainda não expõe seus produtos?</p>
        <RouterLink to="/cadastro-produtor" class="text-sm text-nativo font-bold hover:underline">Cadastre-se como Produtor</RouterLink>
      </div>
    </div>
  </main>
</template>
