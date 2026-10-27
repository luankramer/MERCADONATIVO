<script setup lang="ts">
/** Curadoria de publicações: filtros por status/categoria e análise de cada produto. */
import { inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmarComMotivo } from '@/services/confirm'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'
import { CATEGORIAS, NOME_CATEGORIA } from '@/utils/categorias'
import AnalyzeModal from './AnalyzeModal.vue'

const route = useRoute()
const router = useRouter()
const atualizarPendentes = inject<() => void>('atualizarPendentes', () => {})

const status = ref('pendente')
const categoria = ref('Todas')
const lista = ref<any[]>([])
const carregando = ref(true)
const analisando = ref<number | null>(route.query.analisar ? Number(route.query.analisar) : null)

const STATUS: Record<string, { texto: string; classe: string; icone: string }> = {
  pendente: { texto: 'Pendente', classe: 'bg-amber-100 text-amber-800', icone: 'image' },
  aprovado: { texto: 'Aprovado', classe: 'bg-green-100 text-green-700', icone: 'check' },
  rejeitado: { texto: 'Rejeitado', classe: 'bg-red-100 text-red-700', icone: 'x' },
}

async function carregar() {
  carregando.value = true
  try {
    lista.value = await api('/api/v1/admin/products', { auth: 'admin', params: { status: status.value, categoria: categoria.value } })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
}

function fecharAnalise() {
  analisando.value = null
  if (route.query.analisar) router.replace({ query: {} })
}

async function excluir(p: any) {
  const motivo = await confirmarComMotivo({
    titulo: `Excluir "${p.nome}"?`,
    texto: 'A publicação sai da vitrine para sempre, com fotos e avaliações. Pedidos antigos continuam no histórico.',
    motivo: { rotulo: 'Motivo (o vendedor recebe pelo WhatsApp)', placeholder: 'Ex.: produto proibido pelas Regras para Vendedores' },
    sim: 'Sim, excluir publicação', nao: 'Não, manter', perigo: true,
  })
  if (motivo === null) return
  try {
    const r = await api<{ message: string }>(`/api/v1/admin/products/${p.id}`, { method: 'DELETE', auth: 'admin', params: { motivo: motivo || undefined } })
    toast.sucesso(r.message)
    aoAlterar()
  } catch (e) {
    toast.erro(e)
  }
}

function aoAlterar() {
  carregar()
  atualizarPendentes()
}

watch([status, categoria], carregar)
onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <div class="card p-6">
      <h2 class="font-serif text-lg font-bold text-slate-900 flex items-center gap-2 mb-4"><Icon name="filter" class="w-5 h-5 text-nativo" /> Filtros de Curadoria</h2>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-slate-600">Status</label>
          <select v-model="status" class="input-soft mt-1">
            <option value="pendente">Pendente</option><option value="aprovado">Aprovado</option>
            <option value="rejeitado">Rejeitado</option><option value="todos">Todos</option>
          </select>
        </div>
        <div>
          <label class="text-xs font-semibold uppercase tracking-wider text-slate-600">Categoria</label>
          <select v-model="categoria" class="input-soft mt-1">
            <option value="Todas">Todas as Categorias</option>
            <option v-for="c in CATEGORIAS" :key="c" :value="c">{{ NOME_CATEGORIA[c] }}</option>
          </select>
        </div>
      </div>
    </div>

    <div class="card overflow-hidden">
      <h2 class="font-serif text-lg font-bold text-slate-900 px-6 py-5">Publicações Submetidas</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[640px]">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-600 border-y border-slate-100">
            <tr>
              <th class="px-6 py-3 text-left font-semibold">Produto</th>
              <th class="px-4 py-3 text-left font-semibold">Produtor / Local</th>
              <th class="px-4 py-3 text-left font-semibold">Status</th>
              <th class="px-6 py-3 text-right font-semibold">Ação</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="carregando"><td colspan="4" class="px-6 py-8"><div class="h-10 bg-slate-100 rounded-lg animate-pulse" /></td></tr>
            <tr v-for="p in lista" v-else :key="p.id" class="hover:bg-slate-50/60">
              <td class="px-6 py-3">
                <div class="flex items-center gap-3">
                  <span class="w-10 h-10 shrink-0 rounded-lg overflow-hidden border border-slate-100"><ImageBox :src="p.imagem" icon-class="w-4 h-4 text-slate-300" /></span>
                  <span class="font-semibold text-slate-900">{{ p.nome }}</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <p class="text-slate-800 flex items-center gap-1">{{ p.produtor?.nome_loja }} <Icon v-if="p.produtor?.premium" name="star" filled class="w-3.5 h-3.5 text-amber-400" /></p>
                <p class="text-xs text-slate-600">{{ p.produtor?.local }}</p>
              </td>
              <td class="px-4 py-3">
                <span :class="['badge normal-case rounded-full px-2.5 py-1', STATUS[p.status]?.classe]"><Icon :name="STATUS[p.status]?.icone || 'image'" class="w-3 h-3" /> {{ STATUS[p.status]?.texto }}</span>
                <span v-if="p.analise_ia" class="ml-2 text-xs text-slate-500" title="Adequação na verificação automática">{{ p.analise_ia.score }}%</span>
              </td>
              <td class="px-6 py-3 text-right">
                <button v-if="p.status === 'pendente'" class="text-nativo font-medium inline-flex items-center gap-1 hover:underline" @click="analisando = p.id"><Icon name="search" class="w-4 h-4" /> Analisar</button>
                <button v-else class="text-slate-600 inline-flex items-center gap-1 hover:text-slate-800" @click="analisando = p.id"><Icon name="eye" class="w-4 h-4" /> Detalhes</button>
                <button class="ml-4 text-red-600 font-medium inline-flex items-center gap-1 hover:underline" @click="excluir(p)"><Icon name="trash" class="w-4 h-4" /> Excluir</button>
              </td>
            </tr>
            <tr v-if="!carregando && !lista.length"><td colspan="4" class="px-6 py-10 text-center text-slate-600">Nenhuma publicação com esses filtros.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <AnalyzeModal :product-id="analisando" @fechar="fecharAnalise" @alterado="aoAlterar" />
  </div>
</template>
