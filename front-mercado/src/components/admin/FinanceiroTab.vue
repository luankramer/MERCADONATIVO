<script setup lang="ts">
/**
 * Financeiro do mês: o que entrou na conta Mercado Pago do Mercado Nativo, as taxas do Mercado Pago,
 * a comissão e quanto repassar a cada produtor (vendas de quem não tinha a conta conectada).
 * Só o Super Admin registra repasses. A planilha (CSV) abre no Excel.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api, API_URL } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import { confirmarComMotivo } from '@/services/confirm'
import { moeda, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

interface Repasse { id: number; valor: number; pago_em: string; observacao: string }
interface LinhaProdutor {
  producer_id: number; loja: string; nome: string; whatsapp: string
  pedidos_direto: number; pedidos_plataforma: number
  vendas: number; taxa_mercadopago: number; comissao: number
  recebeu_direto: number; a_repassar: number; repassado: number
  situacao: 'pendente' | 'pago' | 'sem_repasse'; repasses: Repasse[]
}
interface Pedido {
  id: number; pago_em: string; loja: string; itens: string; metodo: string; status: string
  valor: number; taxa_mercadopago: number; taxa_real: boolean; comissao: number; produtor_recebe: number
  caminho: 'direto' | 'plataforma'; repasse_id: number | null
}
interface Relatorio {
  mes: string
  taxas_tabela: { pix: number; credito: number; debito: number; comissao: number }
  resumo: {
    pedidos: number; vendas: number; taxa_mercadopago: number; comissao: number; entrou_na_plataforma: number
    a_repassar: number; repassado: number; recebido_direto_pelos_produtores: number; cancelados: number
  }
  produtores: LinhaProdutor[]
  pedidos: Pedido[]
  ajustes: { id: number; loja: string; valor: number; repasse_id: number }[]
}

function mesAtual() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const mes = ref(mesAtual())
const dados = ref<Relatorio | null>(null)
const carregando = ref(false)
const baixando = ref(false)
const verPedidos = ref(false)
const souSuper = computed(() => session.adminSuper)

const nomeMes = computed(() => {
  const [a, m] = mes.value.split('-').map(Number)
  return new Date(a!, (m ?? 1) - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
})

async function carregar() {
  carregando.value = true
  try {
    dados.value = await api<Relatorio>('/api/v1/admin/financeiro', { auth: 'admin', params: { mes: mes.value } })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
}
onMounted(carregar)
watch(mes, carregar)

async function baixarPlanilha() {
  baixando.value = true
  try {
    const r = await fetch(`${API_URL}/api/v1/admin/financeiro/relatorio.csv?mes=${mes.value}`, {
      headers: { Authorization: `Bearer ${session.adminToken}` },
    })
    if (!r.ok) throw new Error('Não foi possível gerar a planilha.')
    const url = URL.createObjectURL(await r.blob())
    const a = document.createElement('a')
    a.href = url
    a.download = `mercado-nativo-financeiro-${mes.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.erro(e)
  } finally {
    baixando.value = false
  }
}

async function registrarRepasse(p: LinhaProdutor) {
  const obs = await confirmarComMotivo({
    titulo: `Confirmar o repasse de ${moeda(p.a_repassar)} para ${p.loja}?`,
    texto: `Faça primeiro o Pix para o produtor (combine a chave pelo WhatsApp ${telefone(p.whatsapp)}). `
      + `Depois de confirmar, as vendas de ${nomeMes.value} dele aparecem como "repasse feito" no painel do produtor.`,
    sim: 'Sim, já fiz o Pix',
    motivo: { rotulo: 'Comprovante ou observação (opcional)', placeholder: 'Ex.: Pix enviado, ID E1234…' },
  })
  if (obs === null) return
  try {
    await api('/api/v1/admin/financeiro/repasses', {
      method: 'POST', auth: 'admin', body: { mes: mes.value, producer_id: p.producer_id, observacao: obs || null },
    })
    toast.sucesso('Repasse registrado.')
    carregar()
  } catch (e) {
    toast.erro(e)
  }
}

const pct = (v: number) => String(v).replace('.', ',')
const SITUACAO: Record<string, string> = { pago: 'Pago', retirado: 'Retirado', cancelado: 'Devolvido' }
</script>

<template>
  <div class="space-y-6">
    <div class="card p-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <label class="label" for="fin-mes">Mês das vendas</label>
        <input id="fin-mes" v-model="mes" type="month" class="input w-52" :max="mesAtual()" />
      </div>
      <button class="btn-dark" :disabled="baixando || !dados" @click="baixarPlanilha">
        <Icon :name="baixando ? 'loader' : 'download'" class="w-5 h-5" /> Baixar relatório (Excel)
      </button>
    </div>

    <div v-if="carregando && !dados" class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="h-28 card animate-pulse" />
    </div>

    <template v-else-if="dados">
      <!-- Resumo do mês -->
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card p-5">
          <p class="text-xs uppercase tracking-wider text-slate-600 font-medium">Total vendido</p>
          <p class="text-2xl font-bold text-slate-900 mt-1">{{ moeda(dados.resumo.vendas) }}</p>
          <p class="text-sm text-slate-600">{{ dados.resumo.pedidos }} pedido(s) pagos<span v-if="dados.resumo.cancelados"> · {{ dados.resumo.cancelados }} devolvido(s)</span></p>
        </div>
        <div class="card p-5">
          <p class="text-xs uppercase tracking-wider text-slate-600 font-medium">Entrou na conta do Mercado Nativo</p>
          <p class="text-2xl font-bold text-nativo mt-1">{{ moeda(dados.resumo.entrou_na_plataforma) }}</p>
          <p class="text-sm text-slate-600">já sem a taxa do Mercado Pago</p>
        </div>
        <div class="card p-5">
          <p class="text-xs uppercase tracking-wider text-slate-600 font-medium">Taxas e comissão</p>
          <p class="text-sm text-slate-700 mt-2">Mercado Pago: <strong>{{ moeda(dados.resumo.taxa_mercadopago) }}</strong></p>
          <p class="text-sm text-slate-700">Comissão Mercado Nativo: <strong>{{ moeda(dados.resumo.comissao) }}</strong></p>
        </div>
        <div :class="['rounded-2xl border-2 p-5', dados.resumo.a_repassar > 0 ? 'border-amber-300 bg-amber-50' : 'border-nativo-light bg-nativo-soft']">
          <p class="text-xs uppercase tracking-wider font-medium" :class="dados.resumo.a_repassar > 0 ? 'text-amber-900' : 'text-nativo-dark'">A repassar aos produtores</p>
          <p class="text-2xl font-bold mt-1" :class="dados.resumo.a_repassar > 0 ? 'text-amber-900' : 'text-nativo'">{{ moeda(dados.resumo.a_repassar) }}</p>
          <p class="text-sm text-slate-700">já repassado: {{ moeda(dados.resumo.repassado) }}</p>
        </div>
      </div>

      <div v-if="dados.ajustes.length" class="rounded-2xl border-2 border-red-200 bg-red-50 p-5 text-red-800" role="alert">
        <p class="font-bold flex items-center gap-2"><Icon name="alert" class="w-5 h-5" /> Pedidos devolvidos depois do repasse</p>
        <p class="text-sm mt-1">O cliente recebeu o dinheiro de volta, mas o produtor já tinha recebido o repasse. Desconte no próximo repasse:</p>
        <ul class="text-sm mt-2 list-disc pl-5">
          <li v-for="a in dados.ajustes" :key="a.id">Pedido nº {{ a.id }} ({{ a.loja }}): {{ moeda(a.valor) }} · repasse nº {{ a.repasse_id }}</li>
        </ul>
      </div>

      <!-- Repasses por produtor -->
      <div class="card overflow-hidden">
        <div class="bg-slate-900 text-white px-6 py-4">
          <h2 class="font-serif text-lg flex items-center gap-2"><Icon name="wallet" class="w-5 h-5" /> Repasses de {{ nomeMes }}</h2>
          <p class="text-sm text-white/80">Venda − taxa do Mercado Pago − comissão de {{ dados.taxas_tabela.comissao }}%. Pague até o 5º dia útil do mês seguinte.</p>
        </div>
        <p v-if="!dados.produtores.length" class="p-6 text-slate-600">Nenhuma venda paga neste mês.</p>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm min-w-[760px]">
            <thead class="text-xs uppercase tracking-wider text-slate-600 bg-slate-50 border-b border-slate-100">
              <tr>
                <th class="px-5 py-3 text-left font-semibold">Produtor</th>
                <th class="px-3 py-3 text-right font-semibold">Vendas</th>
                <th class="px-3 py-3 text-right font-semibold">Taxa MP</th>
                <th class="px-3 py-3 text-right font-semibold">Comissão</th>
                <th class="px-3 py-3 text-right font-semibold">Recebeu direto</th>
                <th class="px-3 py-3 text-right font-semibold">A repassar</th>
                <th class="px-5 py-3 text-right font-semibold">Situação</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="p in dados.produtores" :key="p.producer_id">
                <td class="px-5 py-4">
                  <p class="font-semibold text-slate-900">{{ p.loja }}</p>
                  <p class="text-xs text-slate-600">{{ p.nome }} · {{ telefone(p.whatsapp) }}</p>
                  <p class="text-xs text-slate-500">{{ p.pedidos_direto }} direto na conta dele · {{ p.pedidos_plataforma }} pela conta do Mercado Nativo</p>
                </td>
                <td class="px-3 py-4 text-right tabular-nums whitespace-nowrap">{{ moeda(p.vendas) }}</td>
                <td class="px-3 py-4 text-right tabular-nums whitespace-nowrap text-slate-600">− {{ moeda(p.taxa_mercadopago) }}</td>
                <td class="px-3 py-4 text-right tabular-nums whitespace-nowrap text-slate-600">− {{ moeda(p.comissao) }}</td>
                <td class="px-3 py-4 text-right tabular-nums whitespace-nowrap">{{ moeda(p.recebeu_direto) }}</td>
                <td class="px-3 py-4 text-right tabular-nums whitespace-nowrap font-bold" :class="p.a_repassar > 0 ? 'text-amber-800' : 'text-slate-400'">{{ moeda(p.a_repassar) }}</td>
                <td class="px-5 py-4 text-right">
                  <button v-if="p.situacao === 'pendente' && souSuper" class="btn-primary px-3 py-2 text-sm" @click="registrarRepasse(p)">
                    <Icon name="check" class="w-4 h-4" /> Registrar repasse
                  </button>
                  <span v-else-if="p.situacao === 'pendente'" class="badge normal-case bg-amber-100 text-amber-800">Pendente</span>
                  <span v-else-if="p.situacao === 'pago'" class="badge normal-case bg-green-50 text-green-700">Repassado</span>
                  <span v-else class="text-xs text-slate-500">Sem repasse (recebeu direto)</span>
                  <p v-for="r in p.repasses" :key="r.id" class="text-xs text-slate-500 mt-1">
                    nº {{ r.id }}: {{ moeda(r.valor) }} em {{ r.pago_em }}<span v-if="r.observacao"> · {{ r.observacao }}</span>
                  </p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pedidos do mês -->
      <div class="card overflow-hidden">
        <button class="w-full px-6 py-4 flex items-center justify-between font-semibold text-slate-900 hover:bg-slate-50" @click="verPedidos = !verPedidos">
          <span>Pedidos do mês ({{ dados.pedidos.length }})</span>
          <Icon :name="verPedidos ? 'minus' : 'plus'" class="w-5 h-5" />
        </button>
        <div v-if="verPedidos" class="overflow-x-auto border-t border-slate-100">
          <table class="w-full text-sm min-w-[860px]">
            <thead class="text-xs uppercase tracking-wider text-slate-600 bg-slate-50">
              <tr>
                <th class="px-4 py-2 text-left">Nº</th><th class="px-3 py-2 text-left">Pago em</th><th class="px-3 py-2 text-left">Loja</th>
                <th class="px-3 py-2 text-left">Forma</th><th class="px-3 py-2 text-right">Venda</th><th class="px-3 py-2 text-right">Taxa MP</th>
                <th class="px-3 py-2 text-right">Comissão</th><th class="px-3 py-2 text-right">Produtor</th><th class="px-4 py-2 text-left">Onde caiu</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="o in dados.pedidos" :key="o.id" :class="o.status === 'cancelado' ? 'text-slate-400 line-through' : ''">
                <td class="px-4 py-2">{{ o.id }}</td>
                <td class="px-3 py-2 whitespace-nowrap">{{ o.pago_em }}</td>
                <td class="px-3 py-2">{{ o.loja }}<span class="block text-xs text-slate-500 no-underline">{{ SITUACAO[o.status] || o.status }}</span></td>
                <td class="px-3 py-2">{{ o.metodo }}</td>
                <td class="px-3 py-2 text-right tabular-nums whitespace-nowrap">{{ moeda(o.valor) }}</td>
                <td class="px-3 py-2 text-right tabular-nums whitespace-nowrap" :title="o.taxa_real ? 'Taxa informada pelo Mercado Pago' : 'Estimada pela tabela'">{{ moeda(o.taxa_mercadopago) }}{{ o.taxa_real ? '' : '*' }}</td>
                <td class="px-3 py-2 text-right tabular-nums whitespace-nowrap">{{ moeda(o.comissao) }}</td>
                <td class="px-3 py-2 text-right tabular-nums whitespace-nowrap font-semibold">{{ moeda(o.produtor_recebe) }}</td>
                <td class="px-4 py-2">{{ o.caminho === 'direto' ? 'Conta do produtor' : (o.repasse_id ? `Repasse nº ${o.repasse_id}` : 'Mercado Nativo (pendente)') }}</td>
              </tr>
            </tbody>
          </table>
          <p class="px-4 py-3 text-xs text-slate-500">* Taxa estimada pela tabela do Mercado Pago (Pix {{ pct(dados.taxas_tabela.pix) }}%, crédito {{ pct(dados.taxas_tabela.credito) }}%, débito {{ pct(dados.taxas_tabela.debito) }}%). Sem asterisco: taxa real informada pelo Mercado Pago.</p>
        </div>
      </div>
    </template>
  </div>
</template>
