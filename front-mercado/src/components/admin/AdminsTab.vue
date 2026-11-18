<script setup lang="ts">
/** Gestão da equipe administrativa. Só o Super Admin cadastra, edita e exclui. */
import { onMounted, reactive, ref } from 'vue'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import { confirmar } from '@/services/confirm'
import Icon from '@/components/ui/Icon.vue'

interface AdminItem { id: number; nome: string; email: string; whatsapp: string; nivel: string; is_super: boolean; principal?: boolean }

const admins = ref<AdminItem[]>([])
const form = reactive({ nome: '', email: '', whatsapp: '', senha: '' })
const idEdicao = ref<number | null>(null)
const isLoading = ref(false)
const isMasterAdmin = ref(session.adminSuper)
const meuId = ref<number | null>(null)

async function fetchAdmins() {
  try {
    admins.value = await api<AdminItem[]>('/api/v1/auth/admin/list', { auth: 'admin' })
    const eu = await api<AdminItem>('/api/v1/auth/admin/me', { auth: 'admin' })
    isMasterAdmin.value = eu.is_super
    meuId.value = eu.id
  } catch (e) {
    toast.erro(e)
  }
}
onMounted(fetchAdmins)

async function salvarAdmin() {
  isLoading.value = true
  try {
    if (idEdicao.value) {
      await api(`/api/v1/auth/admin/${idEdicao.value}`, { method: 'PUT', auth: 'admin', body: { ...form, senha: form.senha || null } })
      toast.sucesso('Administrador atualizado!')
    } else {
      await api('/api/v1/auth/admin/register', { method: 'POST', auth: 'admin', body: form })
      toast.sucesso('Acesso criado com sucesso!')
    }
    cancelarEdicao()
    fetchAdmins()
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}

function prepararEdicao(admin: AdminItem) {
  idEdicao.value = admin.id
  Object.assign(form, { nome: admin.nome, email: admin.email, whatsapp: formatarWhatsapp(admin.whatsapp), senha: '' })
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
}

function cancelarEdicao() {
  idEdicao.value = null
  Object.assign(form, { nome: '', email: '', whatsapp: '', senha: '' })
}

/** 68981071483 -> (68) 9 8107-1483 */
function formatarWhatsapp(numero: string) {
  const d = (numero || '').replace(/\D/g, '')
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d[2]} ${d.slice(3, 7)}-${d.slice(7)}`
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return d
}

async function excluirAdmin(admin: AdminItem) {
  if (!(await confirmar({ titulo: `Remover o acesso de ${admin.nome}?`, texto: 'Essa pessoa não vai mais conseguir entrar no painel administrativo.', sim: 'Sim, remover', perigo: true }))) return
  try {
    await api(`/api/v1/auth/admin/${admin.id}`, { method: 'DELETE', auth: 'admin' })
    toast.sucesso('Administrador removido.')
    fetchAdmins()
  } catch (e) {
    toast.erro(e)
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="card overflow-hidden">
      <div class="bg-slate-900 text-white px-6 py-5">
        <h2 class="font-serif text-lg flex items-center gap-2"><Icon name="shield" class="w-5 h-5" /> Equipe Administrativa</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[520px]">
          <thead class="text-xs uppercase tracking-wider text-slate-600 bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-6 py-3 text-left font-semibold">Nome e E-mail</th>
              <th class="px-4 py-3 text-left font-semibold">Nível de Acesso</th>
              <th v-if="isMasterAdmin" class="px-6 py-3 text-right font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="admin in admins" :key="admin.id">
              <td class="px-6 py-4">
                <p class="font-semibold text-slate-900">{{ admin.nome }}</p>
                <p class="text-xs text-slate-600">{{ admin.email }}</p>
                <p v-if="admin.whatsapp" class="text-xs text-slate-600">WhatsApp: {{ formatarWhatsapp(admin.whatsapp) }}</p>
                <p v-else-if="isMasterAdmin" class="text-xs text-amber-700">Sem WhatsApp: não recebe o código de recuperação</p>
              </td>
              <td class="px-4 py-4">
                <span :class="['badge normal-case rounded-full px-2.5 py-1', admin.is_super ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-600']">{{ admin.nivel }}</span>
              </td>
              <td v-if="isMasterAdmin" class="px-6 py-4 text-right whitespace-nowrap">
                <button class="p-2 text-slate-500 hover:text-slate-900" title="Editar" @click="prepararEdicao(admin)"><Icon name="edit" class="w-5 h-5" /></button>
                <button v-if="!admin.principal && admin.id !== meuId" class="p-2 text-slate-500 hover:text-red-600" title="Excluir" :aria-label="`Excluir o acesso de ${admin.email}`" @click="excluirAdmin(admin)"><Icon name="trash" class="w-5 h-5" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <form v-if="isMasterAdmin" class="card p-6 sm:p-8" @submit.prevent="salvarAdmin">
      <h3 class="font-serif text-lg font-bold text-slate-900 pb-4 mb-5 border-b border-slate-100">{{ idEdicao ? 'Editar Acesso' : 'Cadastrar Novo Acesso' }}</h3>
      <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div><label class="label">Nome Completo</label><input v-model="form.nome" required minlength="2" class="input" placeholder="Ex: João da Silva" /></div>
        <div><label class="label">E-mail Institucional</label><input v-model="form.email" type="email" required class="input" placeholder="nome@mercadonativo.com" /></div>
        <div>
          <label class="label">WhatsApp (recuperar a senha)</label>
          <input v-model="form.whatsapp" type="tel" inputmode="tel" autocomplete="tel" class="input" placeholder="(68) 9 9999-9999" />
        </div>
        <div>
          <label class="label">{{ idEdicao ? 'Nova Senha (opcional)' : 'Senha Inicial' }}</label>
          <input v-model="form.senha" type="password" :required="!idEdicao" minlength="8" class="input" autocomplete="new-password" />
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <button v-if="idEdicao" type="button" class="btn-ghost" @click="cancelarEdicao">Cancelar</button>
        <button type="submit" class="btn-dark" :disabled="isLoading">
          <Icon :name="isLoading ? 'loader' : idEdicao ? 'check' : 'plus'" class="w-4 h-4" /> {{ idEdicao ? 'Atualizar Acesso' : 'Salvar Administrador' }}
        </button>
      </div>
    </form>
    <p v-else class="text-sm text-slate-600">Apenas o Super Admin pode cadastrar ou editar administradores.</p>
  </div>
</template>
