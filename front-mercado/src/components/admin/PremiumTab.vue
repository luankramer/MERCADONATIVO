<script setup lang="ts">
/** Vitrine Premium: quais produtos dos assinantes aparecem em destaque no topo. */
import { computed, onMounted, ref } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmar } from '@/services/confirm'
import Icon from '@/components/ui/Icon.vue'
import Toggle from '@/components/ui/Toggle.vue'

const produtores = ref<any[]>([])
const carregando = ref(true)
const premium = computed(() => produtores.value.filter((p) => p.premium))
const gratuitos = computed(() => produtores.value.filter((p) => !p.premium))

async function carregar() {
  try { produtores.value = await api('/api/v1/admin/premium', { auth: 'admin' }) } catch (e) { toast.erro(e) } finally { carregando.value = false }
}

async function alterarDestaque(produto: any, valor: boolean) {
  try {
    await api(`/api/v1/admin/products/${produto.id}/destaque`, { method: 'PATCH', auth: 'admin', body: { destaque: valor } })
    produto.destaque = valor
    toast.sucesso(valor ? `"${produto.nome}" em destaque na vitrine.` : 'Destaque removido.')
  } catch (e) {
    toast.erro(e)
  }
}

async function alterarPremium(produtor: any, valor: boolean) {
  if (!valor && !(await confirmar({ titulo: `Remover o Premium de ${produtor.nome_loja}?`, texto: 'Os destaques dele serão desligados.', sim: 'Sim, remover', perigo: true }))) return
  try {
    await api(`/api/v1/admin/producers/${produtor.id}/premium`, { method: 'PATCH', auth: 'admin', body: { premium: valor } })
    toast.sucesso(valor ? `${produtor.nome_loja} agora é Premium.` : 'Premium removido.')
    carregar()
  } catch (e) {
    toast.erro(e)
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <div class="card overflow-hidden">
      <div class="px-6 py-5">
        <h2 class="font-serif text-xl font-bold text-destaque flex items-center gap-2"><Icon name="star" filled class="w-5 h-5" /> Destaques Premium</h2>
        <p class="text-sm text-slate-600 mt-1">Controle quais produtos dos assinantes ativos aparecem no topo.</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm min-w-[560px]">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-600 border-y border-slate-100">
            <tr><th class="px-6 py-3 text-left font-semibold">Produtor</th><th class="px-4 py-3 text-left font-semibold">Produto destacado</th><th class="px-6 py-3 text-right font-semibold">Destaque ativo</th></tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="carregando"><td colspan="3" class="px-6 py-8"><div class="h-10 bg-slate-100 rounded-lg animate-pulse" /></td></tr>
            <template v-for="prod in premium" :key="prod.id">
              <tr v-for="(p, i) in prod.produtos" :key="p.id">
                <td class="px-6 py-3">
                  <template v-if="i === 0">
                    <p class="font-semibold text-slate-900 flex items-center gap-1">{{ prod.nome }} <Icon name="star" filled class="w-3.5 h-3.5 text-destaque" /></p>
                    <p class="text-xs text-slate-600">{{ prod.nome_loja }}</p>
                  </template>
                </td>
                <td class="px-4 py-3 text-slate-700">{{ p.nome }}</td>
                <td class="px-6 py-3 text-right"><Toggle :model-value="p.destaque" rotulo @update:model-value="alterarDestaque(p, $event)" /></td>
              </tr>
              <tr v-if="!prod.produtos.length">
                <td class="px-6 py-3 font-semibold text-slate-900">{{ prod.nome }}</td>
                <td class="px-4 py-3 text-slate-500 italic" colspan="2">Nenhum produto aprovado ainda</td>
              </tr>
            </template>
            <tr v-if="!carregando && !premium.length"><td colspan="3" class="px-6 py-8 text-center text-slate-600">Nenhum assinante Premium ativo.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div class="px-6 py-5">
        <h2 class="font-serif text-lg font-bold text-slate-900">Assinaturas</h2>
        <p class="text-sm text-slate-600">Conceda ou remova o plano Premium manualmente (ex.: cortesia ou pagamento fora da plataforma).</p>
      </div>
      <div class="divide-y divide-slate-100 border-t border-slate-100">
        <div v-for="prod in [...premium, ...gratuitos]" :key="prod.id" class="px-6 py-3 flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="font-medium text-slate-900 truncate">{{ prod.nome_loja }} <span class="text-slate-500 font-normal">· {{ prod.nome }}</span></p>
            <p class="text-xs text-slate-600">{{ prod.local }}<span v-if="prod.premium && prod.premium_ate"> · até {{ new Date(prod.premium_ate).toLocaleDateString('pt-BR') }}</span></p>
          </div>
          <Toggle :model-value="prod.premium" @update:model-value="alterarPremium(prod, $event)" />
        </div>
      </div>
    </div>
  </div>
</template>
