<script setup lang="ts">
/** Visão Geral: KPIs, finanças do split, assinaturas Premium e atividade recente. */
import { onMounted, ref } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

const dados = ref<any>(null)

onMounted(async () => {
  try { dados.value = await api('/api/v1/admin/overview', { auth: 'admin' }) } catch (e) { toast.erro(e) }
})
</script>

<template>
  <div v-if="!dados" class="grid sm:grid-cols-3 gap-6"><div v-for="i in 6" :key="i" class="h-28 card animate-pulse" /></div>
  <div v-else class="space-y-6">
    <div class="grid sm:grid-cols-3 gap-5">
      <RouterLink to="/admin/aprovacoes" class="card p-6 flex items-center gap-4 hover:shadow-md transition">
        <span class="w-12 h-12 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center"><Icon name="users" class="w-6 h-6" /></span>
        <span><span class="block text-xs uppercase tracking-wider text-slate-600 font-medium">Pendentes</span>
          <span class="text-3xl font-bold text-slate-900">{{ dados.pendentes }}</span> <span class="text-sm text-slate-500">aguardando</span></span>
      </RouterLink>
      <RouterLink to="/admin/vitrine-premium" class="card p-6 flex items-center gap-4 hover:shadow-md transition">
        <span class="w-12 h-12 rounded-full bg-terra-button text-terra flex items-center justify-center"><Icon name="star" class="w-6 h-6" /></span>
        <span><span class="block text-xs uppercase tracking-wider text-slate-600 font-medium">Premium</span>
          <span class="text-3xl font-bold text-slate-900">{{ dados.premium }}</span> <span class="text-sm text-slate-500">ativos</span></span>
      </RouterLink>
      <div class="card p-6 flex items-center gap-4">
        <span class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center"><Icon name="image" class="w-6 h-6" /></span>
        <span><span class="block text-xs uppercase tracking-wider text-slate-600 font-medium">Ativos</span>
          <span class="text-3xl font-bold text-slate-900">{{ dados.ativos }}</span> <span class="text-sm text-slate-500">na plataforma</span></span>
      </div>
    </div>

    <div class="grid sm:grid-cols-3 gap-5">
      <div class="card p-6">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-600 flex items-center gap-2"><Icon name="chart" class="w-4 h-4 text-blue-500" /> Volume transacionado</p>
        <p class="text-3xl font-bold text-slate-900 mt-3">{{ moeda(dados.financeiro.volume_transacionado) }}</p>
        <p class="text-xs text-slate-500 mt-1">Valor bruto pago pelos clientes</p>
      </div>
      <div class="card p-6 border-emerald-100">
        <p class="text-xs font-semibold uppercase tracking-wider text-emerald-700 flex items-center gap-2"><Icon name="clock" class="w-4 h-4" /> Receita (plataforma)</p>
        <p class="text-3xl font-bold text-emerald-700 mt-3">{{ moeda(dados.financeiro.receita_plataforma) }}</p>
        <p class="text-xs text-slate-600 mt-1">Taxa de intermediação retida ({{ dados.financeiro.percentual_plataforma }}%)</p>
      </div>
      <div class="card p-6">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-600 flex items-center gap-2"><Icon name="arrow-up-right" class="w-4 h-4 text-emerald-600" /> Repasse aos produtores</p>
        <p class="text-3xl font-bold text-slate-900 mt-3">{{ moeda(dados.financeiro.repasse_produtores) }}</p>
        <p class="text-xs text-emerald-600 mt-1 flex items-center gap-1"><Icon name="check-circle" class="w-3.5 h-3.5" /> Liquidado ({{ 100 - dados.financeiro.percentual_plataforma }}%) via split</p>
      </div>
    </div>

    <div class="rounded-2xl bg-slate-900 text-white p-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="font-serif text-xl flex items-center gap-2"><Icon name="star" filled class="w-5 h-5 text-amber-400" /> Receita de Assinaturas Premium</p>
        <p class="text-sm text-slate-500 mt-1">Mensalidades pagas por produtores para acesso ao painel de custos e destaque ({{ moeda(dados.financeiro.preco_premium) }}/mês)</p>
      </div>
      <p class="text-3xl font-bold">{{ moeda(dados.financeiro.receita_premium) }}
        <span class="block text-xs font-normal text-slate-500 text-right">{{ dados.financeiro.assinaturas_pagas }} pagamento(s)</span></p>
    </div>

    <div class="card p-6">
      <h2 class="font-serif text-lg font-bold text-slate-900 mb-2">Atividade Recente</h2>
      <div v-if="dados.atividades.length" class="divide-y divide-slate-100">
        <div v-for="(a, i) in dados.atividades" :key="i" class="py-3.5 flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="text-slate-800 truncate">{{ a.titulo }}</p>
            <p class="text-sm text-slate-600">{{ a.detalhe }}</p>
          </div>
          <RouterLink v-if="a.tipo === 'publicacao' && a.status === 'pendente'" :to="{ path: '/admin/aprovacoes', query: { analisar: a.product_id } }" class="text-sm font-medium text-nativo hover:underline shrink-0">Revisar</RouterLink>
          <span v-else-if="a.tipo === 'publicacao'" :class="['badge normal-case', a.status === 'aprovado' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600']">{{ a.status === 'aprovado' ? 'Aprovado' : 'Rejeitado' }}</span>
          <span v-else class="badge normal-case bg-green-50 text-green-700">Pago</span>
        </div>
      </div>
      <p v-else class="text-sm text-slate-600 py-4">Nenhuma atividade ainda.</p>
    </div>

    <div class="card overflow-hidden">
      <div class="px-6 py-5">
        <h2 class="font-serif text-lg font-bold text-slate-900">Extrato de Split Automático</h2>
        <p class="text-sm text-slate-600">Últimas vendas pagas e como o valor foi dividido</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[640px]">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-600">
            <tr>
              <th class="px-6 py-3 text-left font-semibold">Transação / Cliente</th>
              <th class="px-4 py-3 text-left font-semibold">Produtor (recebedor)</th>
              <th class="px-4 py-3 text-right font-semibold">Valor bruto</th>
              <th class="px-4 py-3 text-right font-semibold text-emerald-700">Repasse produtor</th>
              <th class="px-6 py-3 text-right font-semibold text-emerald-700">Comissão plataforma</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="t in dados.extrato_split" :key="t.id">
              <td class="px-6 py-3">
                <p class="font-semibold text-slate-900"><span class="badge normal-case bg-emerald-50 text-emerald-700 mr-1">{{ t.metodo }}</span>{{ t.descricao }}</p>
                <p class="text-xs text-slate-600">Cliente: {{ t.cliente }}</p>
              </td>
              <td class="px-4 py-3 font-medium text-slate-700">{{ t.produtor }}</td>
              <td class="px-4 py-3 text-right text-slate-600">{{ moeda(t.valor_bruto) }}</td>
              <td class="px-4 py-3 text-right text-emerald-700 font-semibold">↗ {{ moeda(t.repasse_produtor) }}</td>
              <td class="px-6 py-3 text-right"><span class="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-700 font-semibold">+ {{ moeda(t.comissao_plataforma) }}</span></td>
            </tr>
            <tr v-if="!dados.extrato_split.length"><td colspan="5" class="px-6 py-8 text-center text-slate-600">Nenhuma venda paga ainda.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
