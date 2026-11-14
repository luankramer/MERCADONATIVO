<script setup lang="ts">
/** SAC: pedidos de todos os vendedores, com contato do comprador e cancelamento com devolução. */
import { computed, inject, onMounted, ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmar, confirmarComMotivo } from '@/services/confirm'
import { dataHora, moeda, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

interface Pedido {
  id: number; codigo: string; descricao: string; cliente: string; whatsapp: string; produtor: string
  produtor_whatsapp?: string | null
  valor_total: number; metodo: string; gateway: string; status: string; criado_em: string | null; pago_em: string | null
  pode_cancelar: boolean; cancelado_em: string | null; cancelado_por: string | null; motivo_cancelamento: string | null
  reembolso_status: string | null; retirado_em: string | null; prazo_arrependimento: string | null; dentro_do_prazo: boolean
  pix_reserva?: boolean; reserva_informado_em?: string | null
  solicitacao?: { status: string; em: string | null; motivo: string | null; resposta: string | null; respondida_em: string | null } | null
}
interface Servicos {
  pagamentos: string; mercado_pago_respondendo: boolean; pix_reserva_configurado: boolean
  whatsapp_principal: boolean; whatsapp_reserva_meta: boolean; email_reserva: boolean
  avisos_mp_na_fila: number; mensagens_na_fila: number; pix_reserva_a_conferir: number; devolucoes_com_problema: number
}

const lista = ref<Pedido[]>([])
const status = ref('todos')
const pendentes = ref(0)  // pedidos de cancelamento esperando a equipe
const busca = ref('')
const carregando = ref(true)
const cancelando = ref<number | null>(null)
const confirmando = ref<number | null>(null)
const servicos = ref<Servicos | null>(null)

const DEVOLUCAO: Record<string, string> = {
  approved: '· valor devolvido', simulado: '· demonstração', sem_cobranca: '· nada cobrado',
  pending: '· devolução em andamento no Mercado Pago', manual: '· DEVOLVER O PIX MANUALMENTE', falhou: '· DEVOLUÇÃO FALHOU: resolver',
}

async function carregarServicos() {
  try { servicos.value = await api<Servicos>('/api/v1/admin/status-servicos', { auth: 'admin' }) } catch { /* opcional */ }
}

async function confirmarPixReserva(p: Pedido) {
  if (!(await confirmar({
    titulo: `Confirmar o Pix de ${moeda(p.valor_total)} do pedido nº ${p.id}?`,
    texto: 'Só confirme depois de ver o Pix no extrato da conta do Mercado Nativo (identificação MN' + p.id + '). '
      + 'O pedido é liberado e o repasse ao produtor deste pedido deve ser feito manualmente.',
    sim: 'Sim, o Pix caiu', nao: 'Ainda não',
  }))) return
  confirmando.value = p.id
  try {
    const r = await api<any>(`/api/v1/admin/orders/${p.id}/confirmar-pix-reserva`, { method: 'POST', auth: 'admin' })
    Object.assign(p, r)
    toast.sucesso(r.message)
    carregarServicos()
  } catch (e) {
    toast.erro(e)
  } finally {
    confirmando.value = null
  }
}

const STATUS: Record<string, { texto: string; classe: string }> = {
  aguardando_pagamento: { texto: 'Aguardando pagamento', classe: 'bg-amber-50 text-amber-800' },
  pago: { texto: 'Pago · a retirar', classe: 'bg-sky-50 text-sky-800' },
  retirado: { texto: 'Retirado', classe: 'bg-green-50 text-green-800' },
  cancelado: { texto: 'Cancelado', classe: 'bg-red-50 text-red-700' },
}
const QUEM: Record<string, string> = { cliente: 'pelo cliente', produtor: 'pelo produtor', admin: 'pela equipe',
  mercadopago: 'no Mercado Pago', sistema: 'automático (produto saiu da vitrine)' }

const filtrados = computed(() => {
  const t = busca.value.trim().toLowerCase()
  return t ? lista.value.filter((p) => `${p.id} ${p.cliente} ${p.whatsapp} ${p.produtor} ${p.descricao}`.toLowerCase().includes(t)) : lista.value
})

const atualizarMenu = inject<() => void>('atualizarPendentes', () => {})

async function contarPendentes() {
  atualizarMenu()
  try {
    pendentes.value = (await api<{ total: number }>('/api/v1/admin/orders/solicitacoes/total', { auth: 'admin' })).total
  } catch { /* opcional */ }
}

async function carregar() {
  carregando.value = true
  contarPendentes()
  try {
    lista.value = await api<Pedido[]>('/api/v1/admin/orders', { auth: 'admin', params: { status: status.value } })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
}

const pedido = (p: Pedido) => p.solicitacao?.status === 'pendente' && p.status !== 'cancelado'

async function cancelar(p: Pedido) {
  const aviso = (pedido(p) ? 'Só aprove depois de confirmar com o produtor que o produto não foi entregue nem enviado. ' : '')
    + (p.status === 'retirado'
      ? (p.dentro_do_prazo ? 'O cliente está dentro dos 7 dias de arrependimento. ' : 'Atenção: já passou dos 7 dias de arrependimento. ')
      : '')
  const motivo = await confirmarComMotivo({
    titulo: pedido(p) ? `Aprovar o cancelamento do pedido nº ${p.id} e devolver ${moeda(p.valor_total)}?`
      : `Cancelar o pedido nº ${p.id} e devolver ${moeda(p.valor_total)}?`,
    texto: `${aviso}${p.gateway === 'manual'
      ? 'Este pedido foi pago pelo Pix de reserva: depois de cancelar, devolva o Pix ao cliente manualmente pela conta do Mercado Nativo.'
      : 'O valor volta para o cliente pelo Mercado Pago.'} O produto volta ao estoque e cliente e vendedor recebem aviso no WhatsApp. Não dá para desfazer.`,
    motivo: { rotulo: 'Motivo (o cliente e o vendedor recebem)', placeholder: 'Ex.: arrependimento dentro de 7 dias / produto com defeito', obrigatorio: true },
    sim: 'Sim, cancelar e devolver', nao: 'Não, voltar', perigo: true,
  })
  if (motivo === null) return
  cancelando.value = p.id
  try {
    const r = await api<any>(`/api/v1/admin/orders/${p.id}/cancelar`, { method: 'POST', auth: 'admin', body: { motivo } })
    Object.assign(p, r)
    toast.sucesso(r.message)
    contarPendentes()
  } catch (e) {
    toast.erro(e)
  } finally {
    cancelando.value = null
  }
}

async function recusar(p: Pedido) {
  const motivo = await confirmarComMotivo({
    titulo: `Recusar o pedido de cancelamento do pedido nº ${p.id}?`,
    texto: 'Use quando o produtor confirmar que o produto já foi entregue ou enviado. O pedido continua como está, '
      + 'nada é devolvido e o cliente recebe o motivo pelo WhatsApp.',
    motivo: { rotulo: 'Motivo (o cliente recebe)', placeholder: 'Ex.: o produtor entregou o produto no dia 12', obrigatorio: true },
    sim: 'Recusar o pedido de cancelamento', nao: 'Voltar',
  })
  if (motivo === null) return
  cancelando.value = p.id
  try {
    const r = await api<any>(`/api/v1/admin/orders/${p.id}/solicitacao/recusar`, { method: 'POST', auth: 'admin', body: { motivo } })
    Object.assign(p, r)
    toast.sucesso(r.message)
    contarPendentes()
  } catch (e) {
    toast.erro(e)
  } finally {
    cancelando.value = null
  }
}

watch(status, carregar)
onMounted(() => { carregar(); carregarServicos() })
</script>

<template>
  <div class="space-y-6">
    <div class="card p-6 flex flex-wrap items-end gap-4">
      <div class="flex-1 min-w-[14rem]">
        <label class="label" for="busca-pedido">Buscar pedido</label>
        <input id="busca-pedido" v-model="busca" class="input-soft" placeholder="Nº, cliente, WhatsApp, vendedor ou produto" />
      </div>
      <div>
        <label class="label" for="status-pedido">Situação</label>
        <select id="status-pedido" v-model="status" class="input-soft">
          <option value="todos">Todos</option>
          <option value="solicitacoes">Pedidos de cancelamento</option>
          <option value="pago">Pagos (a retirar)</option>
          <option value="retirado">Retirados</option>
          <option value="aguardando_pagamento">Aguardando pagamento</option>
          <option value="cancelado">Cancelados</option>
        </select>
      </div>
      <p class="text-slate-600">{{ filtrados.length }} pedido(s)</p>
    </div>

    <div v-if="servicos" class="card p-4 flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Situação dos serviços">
      <span :class="servicos.pagamentos === 'desativado' ? 'text-red-700 font-semibold'
        : servicos.mercado_pago_respondendo ? 'text-green-700' : 'text-amber-700 font-semibold'">
        <Icon :name="servicos.mercado_pago_respondendo && servicos.pagamentos !== 'desativado' ? 'check' : 'alert'" class="w-4 h-4 inline" />
        Mercado Pago: {{ servicos.pagamentos === 'desativado' ? 'desativado (confira as chaves no .env)'
          : servicos.pagamentos === 'simulado' ? 'modo demonstração'
          : servicos.mercado_pago_respondendo ? 'funcionando' : 'fora do ar (pausado; o sistema tenta de novo sozinho)' }}
      </span>
      <span :class="servicos.pix_reserva_configurado ? 'text-green-700' : 'text-slate-500'">
        Pix de reserva: {{ servicos.pix_reserva_configurado ? 'pronto' : 'não configurado' }}
      </span>
      <span :class="servicos.whatsapp_principal || servicos.whatsapp_reserva_meta ? 'text-green-700' : 'text-red-700 font-semibold'">
        WhatsApp: {{ [servicos.whatsapp_principal && 'principal', servicos.whatsapp_reserva_meta && 'reserva Meta'].filter(Boolean).join(' + ') || 'não configurado' }}
        {{ servicos.email_reserva ? '· e-mail de reserva' : '' }}
      </span>
      <span v-if="servicos.mensagens_na_fila || servicos.avisos_mp_na_fila" class="text-amber-700">
        Na fila para reenviar: {{ servicos.mensagens_na_fila }} mensagem(ns) · {{ servicos.avisos_mp_na_fila }} aviso(s) do Mercado Pago
      </span>
      <span v-if="servicos.pix_reserva_a_conferir" class="text-amber-800 font-semibold">
        {{ servicos.pix_reserva_a_conferir }} Pix de reserva para conferir no extrato
      </span>
      <span v-if="servicos.devolucoes_com_problema" class="text-red-700 font-semibold">
        {{ servicos.devolucoes_com_problema }} devolução(ões) com falha
      </span>
    </div>

    <button v-if="pendentes && status !== 'solicitacoes'" type="button" @click="status = 'solicitacoes'"
            class="w-full text-left rounded-xl border-2 border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 font-semibold flex items-center gap-2">
      <Icon name="alert" class="w-5 h-5 shrink-0" />
      {{ pendentes }} pedido(s) de cancelamento esperando resposta. Toque para ver.
    </button>

    <p class="rounded-xl bg-sky-50 border border-sky-200 px-4 py-3 text-sky-900">
      Pedido ainda não pago o cliente cancela sozinho. Pedido <strong>pago</strong> vira um <strong>pedido de cancelamento</strong>:
      fale com o produtor e confirme se o produto já foi entregue ou enviado. Não foi? <strong>Aprove</strong> (o dinheiro volta).
      Já foi? <strong>Recuse</strong> e informe o motivo. Depois da retirada, o cliente ainda tem <strong>7 dias</strong> para desistir
      (Código de Defesa do Consumidor, art. 49).
    </p>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[900px]">
          <thead class="bg-slate-50 text-slate-700 border-b border-slate-100">
            <tr>
              <th class="px-6 py-3 text-left font-semibold">Pedido</th>
              <th class="px-4 py-3 text-left font-semibold">Cliente</th>
              <th class="px-4 py-3 text-left font-semibold">Vendedor</th>
              <th class="px-4 py-3 text-right font-semibold">Valor</th>
              <th class="px-4 py-3 text-left font-semibold">Situação</th>
              <th class="px-6 py-3 text-right font-semibold">Ação</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="carregando"><td colspan="6" class="px-6 py-8"><div class="h-10 bg-slate-100 rounded-lg animate-pulse" /></td></tr>
            <tr v-for="p in filtrados" v-else :key="p.id" class="align-top hover:bg-slate-50/60">
              <td class="px-6 py-3">
                <p class="font-semibold text-slate-900">nº {{ p.id }} · {{ p.descricao }}</p>
                <p class="text-xs text-slate-500">{{ dataHora(p.pago_em || p.criado_em) }} · {{ p.metodo }}{{ p.gateway === 'simulado' ? ' (demonstração)' : p.gateway === 'manual' ? ' (Pix de reserva)' : '' }}</p>
              </td>
              <td class="px-4 py-3">
                <p class="text-slate-800">{{ p.cliente }}</p>
                <a :href="`https://wa.me/55${p.whatsapp.replace(/\D/g, '')}`" target="_blank" rel="noopener" class="text-nativo hover:underline">{{ telefone(p.whatsapp) }}</a>
              </td>
              <td class="px-4 py-3 text-slate-700">
                <p>{{ p.produtor }}</p>
                <a v-if="p.produtor_whatsapp" :href="`https://wa.me/55${p.produtor_whatsapp.replace(/\D/g, '')}`" target="_blank" rel="noopener"
                   class="text-nativo hover:underline">{{ telefone(p.produtor_whatsapp) }}</a>
              </td>
              <td class="px-4 py-3 text-right font-semibold tabular-nums">{{ moeda(p.valor_total) }}</td>
              <td class="px-4 py-3">
                <span :class="['badge', STATUS[p.status]?.classe]">{{ STATUS[p.status]?.texto || p.status }}</span>
                <p v-if="p.status === 'retirado' && p.prazo_arrependimento" class="text-xs mt-1" :class="p.dentro_do_prazo ? 'text-green-700' : 'text-slate-500'">
                  {{ p.dentro_do_prazo ? 'Dentro dos 7 dias até' : '7 dias encerrados em' }} {{ dataHora(p.prazo_arrependimento) }}
                </p>
                <p v-if="p.status === 'cancelado'" class="text-xs text-slate-600 mt-1 max-w-[16rem]">
                  {{ QUEM[p.cancelado_por || ''] || '' }} em {{ dataHora(p.cancelado_em) }}{{ p.motivo_cancelamento ? ` · ${p.motivo_cancelamento}` : '' }}
                  <span :class="{ 'text-red-700 font-semibold': ['manual', 'falhou'].includes(p.reembolso_status || '') }">
                    {{ DEVOLUCAO[p.reembolso_status || 'sem_cobranca'] || `· devolução: ${p.reembolso_status}` }}
                  </span>
                </p>
                <p v-if="pedido(p)" class="text-xs mt-1 text-amber-800 font-semibold max-w-[16rem]">
                  Cliente pediu cancelamento em {{ dataHora(p.solicitacao?.em || null) }}{{ p.solicitacao?.motivo ? ` · ${p.solicitacao.motivo}` : '' }}.
                  Confirme com o produtor antes de responder.
                </p>
                <p v-else-if="p.solicitacao?.status === 'recusada'" class="text-xs mt-1 text-slate-600 max-w-[16rem]">
                  Pedido de cancelamento recusado{{ p.solicitacao.resposta ? `: ${p.solicitacao.resposta}` : '' }}
                </p>
                <p v-if="p.pix_reserva && p.status === 'aguardando_pagamento'" class="text-xs mt-1"
                   :class="p.reserva_informado_em ? 'text-amber-800 font-semibold' : 'text-slate-500'">
                  {{ p.reserva_informado_em ? `Cliente avisou que pagou em ${dataHora(p.reserva_informado_em)}` : 'Pix de reserva gerado, sem aviso do cliente' }}
                </p>
              </td>
              <td class="px-6 py-3 text-right whitespace-nowrap">
                <div class="flex flex-col items-end gap-2">
                <RouterLink :to="`/pedido/${p.codigo}`" target="_blank" class="text-nativo font-medium inline-flex items-center gap-1 hover:underline"><Icon name="eye" class="w-4 h-4" /> Ver</RouterLink>
                <button v-if="p.pix_reserva && p.status === 'aguardando_pagamento'"
                        :class="['font-medium inline-flex items-center gap-1 hover:underline disabled:opacity-50',
                                 p.reserva_informado_em ? 'text-green-700' : 'text-slate-600']"
                        :disabled="confirmando === p.id" @click="confirmarPixReserva(p)">
                  <Icon :name="confirmando === p.id ? 'loader' : 'check'" class="w-4 h-4" /> Confirmar Pix recebido
                </button>
                <button v-if="pedido(p)" class="text-slate-700 font-medium inline-flex items-center gap-1 hover:underline disabled:opacity-50"
                        :disabled="cancelando === p.id" @click="recusar(p)">
                  <Icon name="x" class="w-4 h-4" /> Recusar
                </button>
                <button v-if="p.pode_cancelar" class="text-red-600 font-medium inline-flex items-center gap-1 hover:underline disabled:opacity-50"
                        :disabled="cancelando === p.id" @click="cancelar(p)">
                  <Icon :name="cancelando === p.id ? 'loader' : pedido(p) ? 'check' : 'x'" class="w-4 h-4" />
                  {{ pedido(p) ? 'Aprovar e devolver' : 'Cancelar e devolver' }}
                </button>
                </div>
              </td>
            </tr>
            <tr v-if="!carregando && !filtrados.length"><td colspan="6" class="px-6 py-10 text-center text-slate-600">Nenhum pedido encontrado.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
