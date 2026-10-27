<script setup lang="ts">
/** Vendedores cadastrados: busca, link para o perfil público e exclusão (só o Super Admin). */
import { computed, onMounted, ref } from 'vue'
import { api } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import { confirmarComMotivo } from '@/services/confirm'
import { dataHora, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

interface Vendedor {
  id: number; nome: string; nome_loja: string; whatsapp: string | null; local: string; premium: boolean
  produtos: number; na_vitrine: number; vendas: number; cadastrado_em: string | null
}

const lista = ref<Vendedor[]>([])
const busca = ref('')
const carregando = ref(true)
const excluindo = ref<number | null>(null)

const filtrados = computed(() => {
  const t = busca.value.trim().toLowerCase()
  return t ? lista.value.filter((v) => `${v.nome} ${v.nome_loja} ${v.local} ${v.whatsapp}`.toLowerCase().includes(t)) : lista.value
})

async function carregar() {
  carregando.value = true
  try {
    lista.value = await api<Vendedor[]>('/api/v1/admin/producers', { auth: 'admin' })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
}

async function excluir(v: Vendedor) {
  const motivo = await confirmarComMotivo({
    titulo: `Excluir o vendedor "${v.nome_loja}"?`,
    texto: `Os ${v.produtos} produto(s) saem da vitrine e os dados pessoais (nome, WhatsApp, endereço, foto) são apagados. `
      + 'Os pedidos já pagos continuam no histórico financeiro, sem dados do vendedor. Não dá para desfazer.',
    motivo: { rotulo: 'Motivo (o vendedor recebe pelo WhatsApp antes da exclusão)', placeholder: 'Ex.: pedido do próprio vendedor / venda de produto proibido' },
    sim: 'Sim, excluir vendedor', nao: 'Não, manter', perigo: true,
  })
  if (motivo === null) return
  excluindo.value = v.id
  try {
    const r = await api<{ message: string }>(`/api/v1/admin/producers/${v.id}`, { method: 'DELETE', auth: 'admin', params: { motivo: motivo || undefined } })
    toast.sucesso(r.message)
    lista.value = lista.value.filter((x) => x.id !== v.id)
  } catch (e) {
    toast.erro(e)
  } finally {
    excluindo.value = null
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <div class="card p-6 flex flex-wrap items-end justify-between gap-4">
      <div class="flex-1 min-w-[16rem]">
        <label class="label" for="busca-vendedor">Buscar vendedor</label>
        <input id="busca-vendedor" v-model="busca" class="input-soft" placeholder="Nome, negócio, cidade ou WhatsApp" />
      </div>
      <p class="text-slate-600">{{ filtrados.length }} de {{ lista.length }} vendedor(es)</p>
    </div>

    <p v-if="!session.adminSuper" class="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-amber-900">
      Só o <strong>Super Admin</strong> pode excluir vendedores. Você pode consultar a lista e excluir publicações na aba Aprovações.
    </p>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[760px]">
          <thead class="bg-slate-50 text-slate-700 border-b border-slate-100">
            <tr>
              <th class="px-6 py-3 text-left font-semibold">Vendedor</th>
              <th class="px-4 py-3 text-left font-semibold">Contato</th>
              <th class="px-4 py-3 text-center font-semibold">Produtos</th>
              <th class="px-4 py-3 text-center font-semibold">Vendas</th>
              <th class="px-6 py-3 text-right font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="carregando"><td colspan="5" class="px-6 py-8"><div class="h-10 bg-slate-100 rounded-lg animate-pulse" /></td></tr>
            <tr v-for="v in filtrados" v-else :key="v.id" class="hover:bg-slate-50/60">
              <td class="px-6 py-3">
                <p class="font-semibold text-slate-900 flex items-center gap-1">{{ v.nome_loja }} <Icon v-if="v.premium" name="star" filled class="w-4 h-4 text-amber-500" /></p>
                <p class="text-slate-600">{{ v.nome }} · {{ v.local }}</p>
                <p v-if="v.cadastrado_em" class="text-xs text-slate-500">Desde {{ dataHora(v.cadastrado_em) }}</p>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ v.whatsapp ? telefone(v.whatsapp) : '-' }}</td>
              <td class="px-4 py-3 text-center"><strong>{{ v.produtos }}</strong> <span class="text-slate-600">({{ v.na_vitrine }} na vitrine)</span></td>
              <td class="px-4 py-3 text-center font-semibold">{{ v.vendas }}</td>
              <td class="px-6 py-3 text-right whitespace-nowrap">
                <RouterLink :to="`/produtor/${v.id}`" target="_blank" class="text-nativo font-medium inline-flex items-center gap-1 hover:underline"><Icon name="eye" class="w-4 h-4" /> Ver perfil</RouterLink>
                <button v-if="session.adminSuper" class="ml-4 text-red-600 font-medium inline-flex items-center gap-1 hover:underline disabled:opacity-50"
                        :disabled="excluindo === v.id" @click="excluir(v)">
                  <Icon :name="excluindo === v.id ? 'loader' : 'trash'" class="w-4 h-4" /> Excluir
                </button>
              </td>
            </tr>
            <tr v-if="!carregando && !filtrados.length"><td colspan="5" class="px-6 py-10 text-center text-slate-600">Nenhum vendedor encontrado.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
