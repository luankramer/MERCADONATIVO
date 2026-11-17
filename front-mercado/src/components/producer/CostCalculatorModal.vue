<script setup lang="ts">
/**
 * Calculadora de Custos (Premium).
 * Cada material é informado como foi comprado e quanto foi usado: kg/g, litro/ml, metro/cm ou unidade.
 *   Ex.: "Paguei R$ 5,50 por 1 kg de açúcar e usei 2 kg"; "Paguei R$ 30 por 12 potes e usei 10";
 *        "Paguei R$ 18 por 500 m de linha e usei 120 m".
 * Soma ainda o tempo de trabalho e outros gastos. O mesmo cálculo é refeito no backend ao salvar.
 */
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'

type Unidade = 'kg' | 'g' | 'L' | 'ml' | 'm' | 'cm' | 'un'
interface Item {
  descricao: string
  preco_compra: number | null
  qtd_compra: number | null
  unidade_compra: Unidade
  qtd_usada: number | null
  unidade_usada: Unidade
}

const props = defineProps<{ aberto: boolean; produtos: { id: number; nome: string }[] }>()
const emit = defineEmits<{ fechar: []; salvo: [] }>()

// unidade -> grandeza e fator para a unidade base (g, ml, cm, un)
const UNIDADES: Record<Unidade, { grupo: string; fator: number; nome: string }> = {
  kg: { grupo: 'massa', fator: 1000, nome: 'kg' },
  g: { grupo: 'massa', fator: 1, nome: 'gramas (g)' },
  L: { grupo: 'volume', fator: 1000, nome: 'litros (L)' },
  ml: { grupo: 'volume', fator: 1, nome: 'ml' },
  m: { grupo: 'comprimento', fator: 100, nome: 'metros (m)' },
  cm: { grupo: 'comprimento', fator: 1, nome: 'cm' },
  un: { grupo: 'unidade', fator: 1, nome: 'unidades' },
}
const TODAS = Object.keys(UNIDADES) as Unidade[]
const mesmasDo = (u: Unidade) => TODAS.filter((x) => UNIDADES[x].grupo === UNIDADES[u].grupo)

// Atalhos: o tipo de material já vem com a unidade certa
const MODELOS: { rotulo: string; icone: string; unidade: Unidade; exemplo: string }[] = [
  { rotulo: 'Ingrediente', icone: 'sprout', unidade: 'kg', exemplo: 'Ex.: Açúcar, polpa, farinha' },
  { rotulo: 'Pote ou embalagem', icone: 'package', unidade: 'un', exemplo: 'Ex.: Pote de vidro, adesivo, tampa' },
  { rotulo: 'Linha, fita ou tecido', icone: 'pen', unidade: 'm', exemplo: 'Ex.: Linha de crochê, barbante, fita' },
  { rotulo: 'Líquido', icone: 'cup', unidade: 'L', exemplo: 'Ex.: Leite, óleo, essência' },
]

function novoItem(unidade: Unidade = 'kg', descricao = ''): Item {
  return { descricao, preco_compra: null, qtd_compra: 1, unidade_compra: unidade, qtd_usada: null, unidade_usada: unidade }
}

const form = reactive({
  nome: '',
  rendimento: 10,
  margem: 50,
  horas_trabalho: 0,
  valor_hora: 0,
  outros_gastos: 0,
  incluir_taxas: true,
  product_id: null as number | null,
  itens: [] as Item[],
})
const salvando = ref(false)
const taxas = ref({ comissao: 10, taxa_pix: 0.99, taxa_cartao: 4.98 })
const historico = ref<any[]>([])
const placeholders = ref<string[]>([])

function limpar() {
  Object.assign(form, {
    nome: '', rendimento: 10, margem: 50, horas_trabalho: 0, valor_hora: 0, outros_gastos: 0,
    incluir_taxas: true, product_id: null,
    itens: [novoItem('kg'), novoItem('un')],
  })
  placeholders.value = [MODELOS[0]!.exemplo, MODELOS[1]!.exemplo]
}

watch(() => props.aberto, async (v) => {
  if (!v) return
  if (!form.itens.length) limpar()
  try { taxas.value = await api('/api/v1/calculadora/config', { auth: 'producer' }) } catch { /* mantém o padrão */ }
  try { historico.value = (await api<any[]>('/api/v1/calculadora/historico', { auth: 'producer' })).filter((h) => h.itens?.[0]?.unidade_compra) } catch { historico.value = [] }
}, { immediate: true })

function adicionar(m: (typeof MODELOS)[number]) {
  form.itens.push(novoItem(m.unidade))
  placeholders.value.push(m.exemplo)
}
function remover(i: number) {
  form.itens.splice(i, 1)
  placeholders.value.splice(i, 1)
}
function trocarUnidadeCompra(item: Item) {
  // A unidade usada precisa ser do mesmo tipo (kg com g, litro com ml, metro com cm)
  if (UNIDADES[item.unidade_usada].grupo !== UNIDADES[item.unidade_compra].grupo) item.unidade_usada = item.unidade_compra
}

function usarCalculo(id: number | string) {
  const h = historico.value.find((x) => x.id === Number(id))
  if (!h) return
  Object.assign(form, {
    nome: h.nome, rendimento: h.rendimento, margem: h.margem,
    horas_trabalho: h.horas_trabalho ?? 0, valor_hora: h.valor_hora ?? 0, outros_gastos: h.outros_gastos ?? 0,
    incluir_taxas: h.incluir_taxas ?? true, product_id: h.product_id ?? null,
    itens: h.itens.map((i: any) => ({ ...novoItem(i.unidade_compra), ...i })),
  })
  placeholders.value = form.itens.map(() => '')
  toast.info(`Cálculo "${h.nome}" carregado. Atualize os preços se mudaram.`)
}

// ----- Contas (iguais às do backend) -----
const arred = (n: number) => Math.round(n * 100 + 1e-6) / 100
const num = (v: number | null | undefined) => (Number.isFinite(Number(v)) ? Number(v) : 0)

function custoItem(i: Item): number | null {
  if (!num(i.preco_compra) && !num(i.qtd_usada)) return null
  if (!(num(i.qtd_compra) > 0)) return null
  const comprado = num(i.qtd_compra) * UNIDADES[i.unidade_compra].fator
  const usado = num(i.qtd_usada) * UNIDADES[i.unidade_usada].fator
  return (num(i.preco_compra) / comprado) * usado
}

const custoMateriais = computed(() => form.itens.reduce((s, i) => s + (custoItem(i) ?? 0), 0))
const custoTrabalho = computed(() => num(form.horas_trabalho) * num(form.valor_hora))
const custoTotal = computed(() => custoMateriais.value + custoTrabalho.value + num(form.outros_gastos))
const custoUnitario = computed(() => (form.rendimento > 0 ? custoTotal.value / form.rendimento : 0))
const percentualTaxas = computed(() => taxas.value.comissao + taxas.value.taxa_cartao)
const precoSugerido = computed(() => {
  const base = custoUnitario.value * (1 + num(form.margem) / 100)
  return arred(form.incluir_taxas ? base / (1 - percentualTaxas.value / 100) : base)
})
function recebe(taxaMp: number) {
  const p = precoSugerido.value
  return arred(p - arred(p * taxas.value.comissao / 100) - arred(p * taxaMp / 100))
}
const lucroUnidade = computed(() => recebe(taxas.value.taxa_cartao) - custoUnitario.value)
const pct = (v: number) => String(v).replace('.', ',')

function escolherProduto() {
  const p = props.produtos.find((x) => x.id === form.product_id)
  if (p && !form.nome) form.nome = p.nome
}

async function salvar() {
  const itens = form.itens
    .filter((i) => i.descricao.trim() || num(i.preco_compra) || num(i.qtd_usada))
    .map((i) => ({ ...i, descricao: i.descricao.trim() || 'Material' }))
  if (!form.nome.trim()) return toast.erro('Informe o que vamos produzir.')
  if (!itens.length) return toast.erro('Adicione pelo menos um material.')
  const incompleto = itens.find((i) => !(num(i.qtd_compra) > 0) || i.preco_compra === null || i.qtd_usada === null)
  if (incompleto) return toast.erro(`Complete o item "${incompleto.descricao}": quanto pagou, quanto comprou e quanto usou.`)
  salvando.value = true
  try {
    const r = await api('/api/v1/calculadora/calcular', {
      method: 'POST', auth: 'producer',
      body: {
        nome: form.nome, rendimento: form.rendimento, margem: form.margem, itens,
        horas_trabalho: num(form.horas_trabalho), valor_hora: num(form.valor_hora), outros_gastos: num(form.outros_gastos),
        incluir_taxas: form.incluir_taxas, product_id: form.product_id, salvar: true,
      },
    })
    toast.sucesso(r.produto_atualizado
      ? `Preço de "${r.produto_atualizado.nome}" atualizado para ${moeda(r.preco_sugerido)}!`
      : `Cálculo salvo! Preço sugerido: ${moeda(r.preco_sugerido)}`)
    limpar()
    emit('salvo')
    emit('fechar')
  } catch (e) {
    toast.erro(e)
  } finally {
    salvando.value = false
  }
}
</script>

<template>
  <Modal :aberto="aberto" titulo="Calculadora de Custos" subtitulo="Ferramenta Exclusiva Premium" icone="calculator" tom="terra" largura="max-w-2xl" @fechar="emit('fechar')">
    <div class="space-y-6">
      <div v-if="historico.length" class="rounded-xl bg-slate-50 border border-slate-200 p-3">
        <label class="label" for="calc-salvo">Começar de um cálculo salvo (opcional)</label>
        <select id="calc-salvo" class="input" @change="usarCalculo(($event.target as HTMLSelectElement).value)">
          <option value="">Começar do zero</option>
          <option v-for="h in historico" :key="h.id" :value="h.id">{{ h.nome }} · {{ h.rendimento }} un. · {{ moeda(h.preco_sugerido) }}</option>
        </select>
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="label font-semibold" for="calc-nome">O que vamos produzir?</label>
          <input id="calc-nome" v-model="form.nome" class="input" placeholder="Ex.: Geleia de goiaba, tapete de crochê" />
        </div>
        <div>
          <label class="label font-semibold" for="calc-rend">Quantas unidades rende?</label>
          <input id="calc-rend" v-model.number="form.rendimento" type="number" min="1" inputmode="numeric" class="input" />
          <p class="text-xs text-slate-500 mt-1">Ex.: 10 potes, 3 tapetes.</p>
        </div>
      </div>

      <!-- Materiais -->
      <section aria-labelledby="calc-materiais">
        <h3 id="calc-materiais" class="font-semibold text-slate-900">Materiais usados</h3>
        <p class="text-sm text-slate-600 mb-3">Diga quanto pagou e quanto usou. Pode ser em kg, gramas, litros, metros ou unidades.</p>

        <div class="space-y-3">
          <div v-for="(item, i) in form.itens" :key="i" class="rounded-2xl border border-slate-200 bg-white p-4">
            <div class="flex items-center gap-2">
              <span class="w-7 h-7 shrink-0 rounded-full bg-terra-light text-terra text-sm font-bold flex items-center justify-center">{{ i + 1 }}</span>
              <input v-model="item.descricao" class="input py-2.5 flex-1 min-w-0" :placeholder="placeholders[i] || 'Nome do material'" :aria-label="`Nome do material ${i + 1}`" />
              <button type="button" class="p-2 text-slate-500 hover:text-red-600" :disabled="form.itens.length === 1" :aria-label="`Remover material ${i + 1}`" @click="remover(i)">
                <Icon name="trash" class="w-5 h-5" />
              </button>
            </div>

            <div class="mt-3 grid grid-cols-1 sm:grid-cols-[auto_1fr] sm:items-center gap-x-3 gap-y-1.5 sm:gap-y-2.5 text-slate-700">
              <span class="text-sm font-semibold">Paguei</span>
              <div class="flex flex-wrap items-center gap-2">
                <div class="relative w-32">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">R$</span>
                  <input v-model.number="item.preco_compra" type="number" min="0" step="0.01" inputmode="decimal" class="input py-2 pl-9" placeholder="0,00" :aria-label="`Preço pago pelo material ${i + 1}`" />
                </div>
                <span class="text-sm">por</span>
                <input v-model.number="item.qtd_compra" type="number" min="0" step="any" inputmode="decimal" class="input py-2 w-24" :aria-label="`Quantidade comprada do material ${i + 1}`" />
                <select v-model="item.unidade_compra" class="input py-2 w-auto" :aria-label="`Unidade da compra do material ${i + 1}`" @change="trocarUnidadeCompra(item)">
                  <option v-for="u in TODAS" :key="u" :value="u">{{ UNIDADES[u].nome }}</option>
                </select>
              </div>

              <span class="text-sm font-semibold mt-2 sm:mt-0">Usei nesta produção</span>
              <div class="flex flex-wrap items-center gap-2">
                <input v-model.number="item.qtd_usada" type="number" min="0" step="any" inputmode="decimal" class="input py-2 w-24" placeholder="0" :aria-label="`Quantidade usada do material ${i + 1}`" />
                <select v-model="item.unidade_usada" class="input py-2 w-auto" :aria-label="`Unidade usada do material ${i + 1}`">
                  <option v-for="u in mesmasDo(item.unidade_compra)" :key="u" :value="u">{{ UNIDADES[u].nome }}</option>
                </select>
                <span class="ml-auto text-right">
                  <span class="block text-xs text-slate-500">custo</span>
                  <strong class="text-lg text-slate-900 tabular-nums">{{ custoItem(item) === null ? '—' : moeda(custoItem(item)!) }}</strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        <p class="text-sm font-semibold text-slate-700 mt-4 mb-2">Adicionar material:</p>
        <div class="grid grid-cols-2 gap-2">
          <button v-for="m in MODELOS" :key="m.rotulo" type="button" class="btn-ghost justify-start text-left py-3" @click="adicionar(m)">
            <Icon :name="m.icone" class="w-5 h-5 text-nativo shrink-0" /> {{ m.rotulo }}
          </button>
        </div>
      </section>

      <!-- Trabalho e outros gastos -->
      <section class="rounded-2xl border border-slate-200 p-4 space-y-4" aria-labelledby="calc-trabalho">
        <div>
          <h3 id="calc-trabalho" class="font-semibold text-slate-900">Seu trabalho (opcional)</h3>
          <p class="text-sm text-slate-600">Quanto vale a sua hora? Ex.: 3 horas de fogão a R$ 10 a hora.</p>
          <div class="flex flex-wrap items-center gap-2 mt-2 text-slate-700">
            <input v-model.number="form.horas_trabalho" type="number" min="0" step="0.5" inputmode="decimal" class="input py-2 w-24" aria-label="Horas de trabalho" />
            <span class="text-sm">horas ×</span>
            <div class="relative w-32">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">R$</span>
              <input v-model.number="form.valor_hora" type="number" min="0" step="0.5" inputmode="decimal" class="input py-2 pl-9" aria-label="Valor da hora" />
            </div>
            <span class="text-sm">por hora = <strong>{{ moeda(custoTrabalho) }}</strong></span>
          </div>
        </div>
        <div>
          <label class="font-semibold text-slate-900" for="calc-outros">Outros gastos desta produção (opcional)</label>
          <p class="text-sm text-slate-600">Gás, energia, água, transporte.</p>
          <div class="relative w-40 mt-2">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-500">R$</span>
            <input id="calc-outros" v-model.number="form.outros_gastos" type="number" min="0" step="0.01" inputmode="decimal" class="input py-2 pl-9" />
          </div>
        </div>
      </section>

      <div>
        <div class="flex justify-between items-center mb-2">
          <label class="font-semibold text-slate-900" for="calc-margem">Quanto quer ganhar além do custo?</label>
          <span class="text-xl font-bold text-nativo">{{ form.margem }}%</span>
        </div>
        <input id="calc-margem" v-model.number="form.margem" type="range" min="0" max="300" step="5" class="w-full accent-nativo" />
      </div>

      <label class="flex items-start gap-3 rounded-xl border border-nativo-light bg-nativo-soft p-3 cursor-pointer">
        <input v-model="form.incluir_taxas" type="checkbox" class="mt-1 w-5 h-5 accent-nativo" />
        <span class="text-sm text-slate-800">
          <strong>Incluir no preço as taxas da venda</strong><br />
          Comissão de {{ pct(taxas.comissao) }}% do Mercado Nativo + até {{ pct(taxas.taxa_cartao) }}% do Mercado Pago no cartão. Assim o seu ganho não diminui.
        </span>
      </label>

      <div>
        <label class="label" for="calc-produto">Aplicar o preço sugerido a um produto (opcional)</label>
        <select id="calc-produto" v-model="form.product_id" class="input" @change="escolherProduto">
          <option :value="null">Não aplicar, só salvar o cálculo</option>
          <option v-for="p in produtos" :key="p.id" :value="p.id">{{ p.nome }}</option>
        </select>
      </div>

      <!-- Resultado -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3" aria-live="polite">
        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 text-center">
          <p class="text-xs font-semibold text-slate-600">Custo total</p>
          <p class="text-lg font-bold text-slate-900">{{ moeda(custoTotal) }}</p>
          <p class="text-[11px] text-slate-500">materiais {{ moeda(custoMateriais) }} · trabalho {{ moeda(custoTrabalho) }} · outros {{ moeda(num(form.outros_gastos)) }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 text-center">
          <p class="text-xs font-semibold text-slate-600">Custo por unidade</p>
          <p class="text-lg font-bold text-red-600">{{ moeda(custoUnitario) }}</p>
        </div>
        <div class="rounded-xl bg-nativo-soft border border-nativo-light p-3 text-center">
          <p class="text-xs font-semibold text-nativo flex items-center justify-center gap-1"><Icon name="trending-up" class="w-3 h-3" /> Preço sugerido</p>
          <p class="text-2xl font-bold text-nativo">{{ moeda(precoSugerido) }}</p>
        </div>
      </div>
      <p v-if="precoSugerido > 0" class="rounded-xl bg-white border border-slate-200 p-3 text-sm text-slate-700">
        Vendendo a <strong>{{ moeda(precoSugerido) }}</strong>, você recebe cerca de <strong>{{ moeda(recebe(taxas.taxa_pix)) }}</strong> no Pix
        e <strong>{{ moeda(recebe(taxas.taxa_cartao)) }}</strong> no cartão.
        Sobra de lucro por unidade: <strong :class="lucroUnidade < 0 ? 'text-red-600' : 'text-nativo'">{{ moeda(lucroUnidade) }}</strong> (no cartão).
      </p>

      <button class="btn-primary w-full py-4" :disabled="salvando" @click="salvar">
        <Icon v-if="salvando" name="loader" class="w-5 h-5" /> Salvar e Precificar
      </button>
    </div>
  </Modal>
</template>
