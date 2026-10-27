<script setup lang="ts">
/** Painel gerencial do produtor: visão financeira, estoque, pedidos, calculadora e plano Premium. */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, assetUrl } from '@/services/api'
import { session } from '@/services/auth'
import { toast } from '@/services/toast'
import { confirmar } from '@/services/confirm'
import { dataHora, iniciais, moeda, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'
import CostCalculatorModal from '@/components/producer/CostCalculatorModal.vue'
import PremiumModal from '@/components/producer/PremiumModal.vue'
import BottomNav from '@/components/ui/BottomNav.vue'
import FontSizeControl from '@/components/ui/FontSizeControl.vue'

const router = useRouter()
const route = useRoute()
const produtor = ref<any>({ nome: '', nome_loja: '', cidade: '', estado: '', premium: false })
const produtos = ref<any[]>([])
const pedidos = ref<any[]>([])
const estatisticas = ref<any>({ visitas: 0, contatos_whatsapp: 0, taxa_conversao: 0, receita_total: 0, receita_30_dias: 0, vendas_concluidas: 0, pendentes_curadoria: 0 })
const carregando = ref(true)
const erroCarga = ref<string | null>(null)
const calculadoraAberta = ref(false)
const premiumAberto = ref(false)

const pedidosAbertos = computed(() => pedidos.value.filter((p) => p.status === 'pago'))
// "De cada 100 pessoas que viram, X chamaram ou compraram" (número inteiro, mais fácil de entender)
const deCada100 = computed(() => Math.round(Number(estatisticas.value.taxa_conversao) || 0))
async function aceitarTermos() {
  try {
    await api('/api/v1/producers/me/aceitar-termos', { method: 'POST', auth: 'producer' })
    produtor.value.termos_pendentes = false
    toast.sucesso('Obrigado! Aceite registrado.')
  } catch (e) {
    toast.erro(e)
  }
}

function irPara(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const todosPedidos = ref(false)
const pedidosVisiveis = computed(() => (todosPedidos.value ? pedidos.value : pedidos.value.slice(0, 3)))

async function carregarDadosDoBanco() {
  erroCarga.value = null
  carregando.value = true
  try {
    const data = await api('/api/v1/dashboard/me', { auth: 'producer' })
    produtor.value = data.produtor
    produtos.value = data.produtos
    estatisticas.value = data.estatisticas
    pedidos.value = await api('/api/v1/producers/me/orders', { auth: 'producer' })
  } catch (e) {
    erroCarga.value = e instanceof Error ? e.message : String(e)
  } finally {
    carregando.value = false
  }
}
onMounted(() => {
  carregarDadosDoBanco()
  if (route.query.premium) { premiumAberto.value = true; router.replace({ query: {} }) }
})

function abrirCalculadora() {
  if (!produtor.value.premium) {
    toast.info('A Calculadora de Custos é exclusiva do plano Premium.')
    premiumAberto.value = true
    return
  }
  calculadoraAberta.value = true
}

async function deletarProduto(item: any) {
  if (!(await confirmar({ titulo: `Excluir "${item.nome}"?`, texto: 'O produto sai da vitrine e não dá para desfazer.', sim: 'Sim, excluir', nao: 'Não, manter o produto', perigo: true }))) return
  try {
    await api(`/api/v1/products/${item.id}`, { method: 'DELETE', auth: 'producer' })
    produtos.value = produtos.value.filter((p) => p.id !== item.id)
    toast.sucesso('Produto removido.')
  } catch (e) {
    toast.erro(e)
  }
}

async function marcarRetirado(pedido: any) {
  try {
    const r = await api(`/api/v1/producers/me/orders/${pedido.id}/retirado`, { method: 'PATCH', auth: 'producer' })
    Object.assign(pedido, r)
    toast.sucesso(`Pedido #${pedido.id} marcado como retirado.`)
  } catch (e) {
    toast.erro(e)
  }
}

function logout() {
  session.logoutProducer()
  router.push('/login-produtor')
}

const STATUS: Record<string, { texto: string; classe: string }> = {
  pendente: { texto: '⏳ Em análise pela equipe', classe: 'bg-amber-50 text-amber-800' },
  aprovado: { texto: '✓ Aparecendo na vitrine', classe: 'bg-green-50 text-green-800' },
  rejeitado: { texto: '✎ Precisa de ajuste', classe: 'bg-red-50 text-red-700' },
}
</script>

<template>
  <main v-if="erroCarga" class="min-h-screen bg-slate-50 flex items-center justify-center p-4">
    <div class="card max-w-md w-full p-8 text-center">
      <div class="w-14 h-14 mx-auto rounded-full bg-red-50 text-red-500 flex items-center justify-center mb-4"><Icon name="alert" class="w-7 h-7" /></div>
      <h1 class="font-serif text-2xl font-bold text-slate-900">Não foi possível abrir o painel</h1>
      <p class="text-sm text-slate-600 mt-2">{{ erroCarga }}</p>
      <div class="flex flex-col gap-2 mt-6">
        <button class="btn-primary" @click="carregarDadosDoBanco"><Icon name="loader" v-if="carregando" class="w-4 h-4" /> Tentar novamente</button>
        <button class="btn-ghost" @click="logout">Voltar ao login</button>
      </div>
    </div>
  </main>
  <div v-else class="min-h-screen bg-slate-100/70">
    <header class="bg-nativo text-white">
      <div class="max-w-6xl mx-auto px-4 py-4 sm:py-5 flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <RouterLink to="/painel/perfil" class="flex items-center gap-3 min-w-0 group">
          <span class="w-14 h-14 shrink-0 rounded-full bg-nativo-dark border-2 border-white/40 flex items-center justify-center font-bold overflow-hidden group-hover:ring-2 ring-white/60 transition">
            <img v-if="produtor.foto_perfil" :src="assetUrl(produtor.foto_perfil)" class="w-full h-full object-cover" alt="" />
            <span v-else>{{ iniciais(produtor.nome) }}</span>
          </span>
          <span class="min-w-0">
            <span class="block font-serif text-2xl font-semibold truncate">Olá, {{ produtor.nome || 'Produtor' }}</span>
            <span class="text-sm text-white/80 flex items-center gap-1 truncate">
              <Icon name="map-pin" class="w-3.5 h-3.5 shrink-0" /> {{ produtor.nome_loja }} • {{ produtor.cidade || '-' }}, {{ produtor.estado }}
            </span>
          </span>
        </RouterLink>
        <div class="flex items-center gap-2 sm:gap-4 w-full sm:w-auto justify-end">
          <button class="text-right hidden sm:block" @click="!produtor.premium && (premiumAberto = true)">
            <span class="block text-sm text-white/80">Seu plano</span>
            <span v-if="produtor.premium" class="font-semibold text-amber-200 flex items-center gap-1"><Icon name="star" filled class="w-4 h-4" /> Premium Ativo</span>
            <span v-else class="font-semibold text-white underline underline-offset-4">Plano Gratuito · Assinar</span>
          </button>
          <FontSizeControl escuro />
          <RouterLink to="/" class="hidden md:inline-flex items-center gap-2 px-3 min-h-[44px] rounded-xl hover:bg-white/10 font-semibold"><Icon name="store" class="w-5 h-5" /> Ver vitrine</RouterLink>
          <button class="inline-flex items-center gap-2 px-3 min-h-[44px] rounded-xl border border-white/30 hover:bg-white/10 font-semibold" @click="logout"><Icon name="log-out" class="w-5 h-5" /> Sair</button>
        </div>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 py-6 sm:py-8 space-y-6 sm:space-y-8 mb-nav">
      <button v-if="!produtor.premium && !carregando" class="sm:hidden w-full rounded-xl bg-terra-light border border-terra-border px-4 py-3 font-semibold text-terra flex items-center gap-2 min-h-[48px]" @click="premiumAberto = true">
        <Icon name="star" class="w-5 h-5" /> Você está no plano gratuito. Conheça o Premium
      </button>

      <section v-if="produtor.termos_pendentes && !carregando" class="rounded-2xl border-2 border-amber-300 bg-amber-50 p-5" role="status">
        <h2 class="text-lg font-bold text-amber-900 flex items-center gap-2"><Icon name="file" class="w-6 h-6" /> Leia as regras do Mercado Nativo</h2>
        <p class="text-amber-900 mt-1">Publicamos os Termos de Uso, as Regras para Vendedores e a Política de Privacidade. Para continuar vendendo, leia e confirme.</p>
        <div class="flex flex-wrap gap-3 mt-4">
          <RouterLink to="/politicas/termos" target="_blank" class="btn-ghost">Ler os Termos</RouterLink>
          <RouterLink to="/politicas/privacidade" target="_blank" class="btn-ghost">Ler a Privacidade</RouterLink>
          <button class="btn-primary" @click="aceitarTermos"><Icon name="check" class="w-5 h-5" /> Li e aceito</button>
        </div>
      </section>

      <!-- O que a pessoa mais faz no painel: três botões grandes -->
      <h1 class="sr-only">Meu painel</h1>
      <nav class="grid grid-cols-1 sm:grid-cols-3 gap-3" aria-label="Ações principais">
        <button class="card p-5 flex items-center gap-4 text-left hover:border-nativo hover:shadow-md transition min-h-[88px]" @click="irPara('pedidos')">
          <span class="relative w-14 h-14 shrink-0 rounded-2xl bg-nativo-light text-nativo flex items-center justify-center">
            <Icon name="package" class="w-7 h-7" />
            <span v-if="pedidosAbertos.length" class="absolute -top-2 -right-2 min-w-[1.75rem] h-7 px-1.5 rounded-full bg-terra text-white text-sm font-bold flex items-center justify-center">{{ pedidosAbertos.length }}</span>
          </span>
          <span>
            <span class="block text-lg font-bold text-slate-900">Pedidos para entregar</span>
            <span class="block text-slate-600">{{ pedidosAbertos.length ? `${pedidosAbertos.length} esperando retirada` : 'Nenhum pedido esperando' }}</span>
          </span>
        </button>
        <RouterLink to="/painel/produto/novo" class="rounded-2xl bg-nativo text-white p-5 flex items-center gap-4 hover:bg-nativo-dark shadow-sm transition min-h-[88px]">
          <span class="w-14 h-14 shrink-0 rounded-2xl bg-white/15 flex items-center justify-center"><Icon name="plus" class="w-8 h-8" /></span>
          <span>
            <span class="block text-lg font-bold">Anunciar produto</span>
            <span class="block text-white/90">Coloque um produto novo à venda</span>
          </span>
        </RouterLink>
        <button class="card p-5 flex items-center gap-4 text-left hover:border-nativo hover:shadow-md transition min-h-[88px]" @click="irPara('estoque')">
          <span class="w-14 h-14 shrink-0 rounded-2xl bg-terra-light text-terra flex items-center justify-center"><Icon name="store" class="w-7 h-7" /></span>
          <span>
            <span class="block text-lg font-bold text-slate-900">Meus produtos</span>
            <span class="block text-slate-600">{{ produtos.length }} cadastrado(s) · editar estoque e preço</span>
          </span>
        </button>
      </nav>

      <section aria-labelledby="titulo-numeros">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h2 id="titulo-numeros" class="font-serif text-2xl font-bold text-slate-900">Como estão suas vendas</h2>
          <button class="btn rounded-xl border-2 border-terra-border bg-terra-light text-terra px-4" @click="abrirCalculadora">
            <Icon name="calculator" class="w-5 h-5" /> Calcular preço de venda
          </button>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <div class="card p-5">
            <p class="font-semibold text-slate-700 flex items-start gap-2"><Icon name="eye" class="w-6 h-6 shrink-0 text-nativo" /> Pessoas que viram seus produtos</p>
            <p class="text-4xl font-bold text-slate-900 mt-2 tabular-nums">{{ estatisticas.visitas }}</p>
          </div>
          <div class="card p-5">
            <p class="font-semibold text-slate-700 flex items-start gap-2"><Icon name="phone" class="w-6 h-6 shrink-0 text-nativo" /> Pessoas que chamaram ou compraram</p>
            <p class="text-4xl font-bold text-slate-900 mt-2 tabular-nums">{{ estatisticas.contatos_whatsapp }}</p>
          </div>
          <div class="card p-5">
            <p class="font-semibold text-slate-700 flex items-start gap-2"><Icon name="wallet" class="w-6 h-6 shrink-0 text-nativo" /> Você recebeu nos últimos 30 dias</p>
            <p class="text-3xl font-bold text-nativo mt-2">{{ moeda(estatisticas.receita_30_dias) }}</p>
            <p class="text-sm text-slate-600 mt-1">{{ estatisticas.vendas_concluidas }} venda(s) · desde o início: {{ moeda(estatisticas.receita_total) }}</p>
          </div>
          <div class="rounded-2xl border-2 border-terra-border bg-terra-light p-5">
            <p class="font-semibold text-terra-dark">De cada 100 pessoas que viram,</p>
            <p class="text-4xl font-bold text-terra mt-1 tabular-nums">{{ deCada100 }}</p>
            <p class="font-semibold text-terra-dark">chamaram você ou compraram</p>
            <div class="mt-3 h-3 rounded-full bg-white overflow-hidden" aria-hidden="true"><div class="h-full bg-terra rounded-full" :style="{ width: `${Math.min(deCada100, 100)}%` }" /></div>
          </div>
        </div>
      </section>

      <!-- Pedidos para retirada -->
      <section v-if="pedidos.length" id="pedidos" class="card overflow-hidden scroll-mt-4">
        <div class="px-6 py-5 border-b border-slate-100">
          <h2 class="font-serif text-2xl font-bold text-slate-900">Pedidos para entregar</h2>
          <p class="text-slate-600">{{ pedidosAbertos.length }} esperando retirada. O estoque já foi descontado sozinho.</p>
        </div>
        <div class="divide-y divide-slate-100">
          <div v-for="p in pedidosVisiveis" :key="p.id" class="px-6 py-4 flex flex-wrap items-center gap-4 justify-between">
            <div class="min-w-0">
              <p class="text-lg font-semibold text-slate-900">{{ p.itens.map((i: any) => `${i.quantidade}× ${i.produto}`).join(', ') }}</p>
              <p class="text-slate-600">{{ p.cliente }} · {{ telefone(p.whatsapp) }}</p>
              <p class="text-sm text-slate-600">Pago com {{ p.metodo }} em {{ dataHora(p.paid_at) }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xl font-bold text-nativo">{{ moeda(p.valor_produtor) }}</span>
              <a :href="`https://wa.me/55${p.whatsapp}`" target="_blank" rel="noopener" class="btn-ghost px-4"><Icon name="phone" class="w-5 h-5" /> Chamar cliente</a>
              <button v-if="p.status === 'pago'" class="btn-primary px-4" @click="marcarRetirado(p)"><Icon name="check" class="w-5 h-5" /> Já retirou</button>
              <span v-else class="badge bg-slate-100 text-slate-600">Retirado</span>
            </div>
          </div>
        </div>
        <button v-if="pedidos.length > 3" class="w-full py-4 font-semibold text-nativo border-t border-slate-100 hover:bg-nativo-soft" @click="todosPedidos = !todosPedidos">
          {{ todosPedidos ? 'Mostrar menos' : `Ver todos os ${pedidos.length} pedidos` }}
        </button>
      </section>

      <!-- Estoque -->
      <section id="estoque" class="card overflow-hidden scroll-mt-4">
        <div class="px-6 py-5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-100">
          <div>
            <h2 class="font-serif text-2xl font-bold text-slate-900">Meus produtos</h2>
            <p class="text-slate-600">Altere preço, quantidade e fotos quando quiser.</p>
          </div>
          <RouterLink to="/painel/produto/novo" class="btn bg-nativo text-white hover:bg-nativo-dark rounded-full px-5 py-2.5">
            <Icon name="plus" class="w-5 h-5" /> Anunciar produto
          </RouterLink>
        </div>

        <div v-if="carregando" class="p-6 space-y-3"><div v-for="i in 3" :key="i" class="h-14 rounded-xl bg-slate-100 animate-pulse" /></div>
        <div v-else-if="!produtos.length" class="p-10 text-center">
          <Icon name="package" class="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p class="font-semibold text-slate-700">Você ainda não cadastrou produtos.</p>
          <p class="text-slate-600">Toque em "Anunciar produto" para colocar o primeiro à venda.</p>
        </div>
        <!-- Celular: lista em cartões -->
        <ul v-else class="md:hidden divide-y divide-slate-100">
          <li v-for="item in produtos" :key="item.id" class="p-4 flex gap-3">
            <span class="w-20 h-20 shrink-0 rounded-xl overflow-hidden"><ImageBox :src="item.imagem" icon-class="w-6 h-6 text-slate-300" /></span>
            <div class="flex-1 min-w-0">
              <p class="text-lg font-semibold text-slate-900 leading-snug">{{ item.nome }}</p>
              <p class="text-sm text-slate-700">{{ moeda(item.preco) }}
                <span :class="['ml-1 badge normal-case', item.estoque > 0 ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600']">{{ item.estoque > 0 ? `${item.estoque} un.` : 'Esgotado' }}</span>
              </p>
              <p class="mt-1"><span :class="['badge', STATUS[item.status]?.classe]">{{ STATUS[item.status]?.texto }}</span></p>
              <p class="text-sm text-slate-600 mt-1">{{ item.views }} pessoas viram · {{ item.conversoes }} chamaram ou compraram</p>
              <p v-if="item.status === 'rejeitado' && item.motivo_rejeicao" class="text-sm text-red-600 mt-1">O que ajustar: {{ item.motivo_rejeicao }}</p>
              <div class="flex gap-2 mt-3">
                <RouterLink :to="`/painel/produto/${item.id}`" class="btn flex-1 bg-nativo-soft text-nativo border border-nativo-light px-3"><Icon name="edit" class="w-5 h-5" /> Editar</RouterLink>
                <button class="btn flex-1 bg-white text-red-600 border border-red-200 px-3" @click="deletarProduto(item)"><Icon name="trash" class="w-5 h-5" /> Excluir</button>
              </div>
            </div>
          </li>
        </ul>
        <!-- Tablet/desktop: tabela -->
        <div v-if="!carregando && produtos.length" class="hidden md:block overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-slate-50 text-sm text-slate-700">
              <tr>
                <th class="px-6 py-3 font-semibold">Produto</th>
                <th class="px-4 py-3 font-semibold">Preço</th>
                <th class="px-4 py-3 font-semibold text-center">Quantidade</th>
                <th class="px-4 py-3 font-semibold">Procura</th>
                <th class="px-6 py-3 font-semibold text-right">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="item in produtos" :key="item.id">
                <td class="px-6 py-3">
                  <div class="flex items-center gap-3">
                    <span class="w-12 h-12 shrink-0 rounded-lg overflow-hidden"><ImageBox :src="item.imagem" icon-class="w-5 h-5 text-slate-300" /></span>
                    <span class="min-w-0">
                      <span class="block font-medium text-slate-900 truncate">{{ item.nome }}</span>
                      <span class="text-sm text-slate-600">{{ item.categoria }}</span>
                      <span :class="['ml-2 badge normal-case', STATUS[item.status]?.classe]" :title="item.motivo_rejeicao || ''">{{ STATUS[item.status]?.texto }}</span>
                    </span>
                  </div>
                  <p v-if="item.status === 'rejeitado' && item.motivo_rejeicao" class="text-sm text-red-600 mt-1">O que ajustar: {{ item.motivo_rejeicao }}</p>
                </td>
                <td class="px-4 py-3 text-slate-700">{{ moeda(item.preco) }}</td>
                <td class="px-4 py-3 text-center">
                  <span v-if="item.estoque > 0" class="badge bg-green-50 text-green-700 normal-case">{{ item.estoque }} un.</span>
                  <span v-else class="badge bg-red-50 text-red-600 normal-case">Esgotado</span>
                </td>
                <td class="px-4 py-3 text-sm">
                  <p><strong class="text-slate-900">{{ item.views }}</strong> <span class="text-slate-600">pessoas viram</span></p>
                  <p><strong class="text-nativo">{{ item.conversoes }}</strong> <span class="text-slate-600">chamaram ou compraram</span></p>
                </td>
                <td class="px-6 py-3 text-right whitespace-nowrap">
                  <RouterLink :to="`/painel/produto/${item.id}`" class="btn px-3 text-nativo hover:bg-nativo-soft"><Icon name="edit" class="w-5 h-5" /> Editar</RouterLink>
                  <button class="btn px-3 text-red-600 hover:bg-red-50" @click="deletarProduto(item)"><Icon name="trash" class="w-5 h-5" /> Excluir</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <CostCalculatorModal :aberto="calculadoraAberta" :produtos="produtos" @fechar="calculadoraAberta = false" @salvo="carregarDadosDoBanco" />
    <PremiumModal :aberto="premiumAberto" @fechar="premiumAberto = false" @ativado="carregarDadosDoBanco" />
    <BottomNav variante="produtor" />
  </div>
</template>
