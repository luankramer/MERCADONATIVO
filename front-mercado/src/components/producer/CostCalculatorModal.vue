<script setup lang="ts">
/** Calculadora de Custos (Premium): custo total, custo por unidade e preço sugerido pela margem. */
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'

const props = defineProps<{ aberto: boolean; produtos: { id: number; nome: string }[] }>()
const emit = defineEmits<{ fechar: []; salvo: [] }>()

const form = reactive({
  nome: '',
  rendimento: 10,
  margem: 50,
  product_id: null as number | null,
  itens: [{ descricao: '', valor: 0 }] as { descricao: string; valor: number }[],
})
const salvando = ref(false)

watch(() => props.aberto, (v) => {
  if (v && !form.nome) {
    Object.assign(form, {
      nome: '', rendimento: 10, margem: 50, product_id: null,
      itens: [{ descricao: '', valor: 0 }, { descricao: '', valor: 0 }],
    })
  }
})

// Mesmo cálculo do backend (arredondamento comercial)
const arred = (n: number) => Math.round(n * 100 + 1e-6) / 100
const custoTotal = computed(() => form.itens.reduce((s, i) => s + (Number(i.valor) || 0), 0))
const custoUnitario = computed(() => (form.rendimento > 0 ? custoTotal.value / form.rendimento : 0))
const precoSugerido = computed(() => arred(custoUnitario.value * (1 + form.margem / 100)))

function escolherProduto() {
  const p = props.produtos.find((x) => x.id === form.product_id)
  if (p && !form.nome) form.nome = p.nome
}

async function salvar() {
  const itens = form.itens.filter((i) => i.descricao.trim() && Number(i.valor) >= 0)
  if (!itens.length) return toast.erro('Adicione pelo menos um ingrediente com valor.')
  if (!form.nome.trim()) return toast.erro('Informe o que vamos produzir.')
  salvando.value = true
  try {
    const r = await api('/api/v1/calculadora/calcular', {
      method: 'POST', auth: 'producer',
      body: { nome: form.nome, rendimento: form.rendimento, margem: form.margem, itens, product_id: form.product_id, salvar: true },
    })
    toast.sucesso(r.produto_atualizado
      ? `Preço de "${r.produto_atualizado.nome}" atualizado para ${moeda(r.preco_sugerido)}!`
      : `Cálculo salvo! Preço sugerido: ${moeda(r.preco_sugerido)}`)
    form.nome = ''
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
    <div class="space-y-5">
      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="label font-semibold">O que vamos produzir?</label>
          <input v-model="form.nome" class="input" placeholder="Ex: Geleia de Cupuaçu" />
        </div>
        <div>
          <label class="label font-semibold">Rendimento (unidades)</label>
          <input v-model.number="form.rendimento" type="number" min="1" class="input" />
        </div>
      </div>

      <div class="card p-4 sm:p-5">
        <p class="font-semibold text-slate-900 mb-3">Ingredientes &amp; Matéria Prima</p>
        <div class="space-y-2.5">
          <div v-for="(item, i) in form.itens" :key="i" class="flex items-center gap-2">
            <span class="text-xs text-slate-500 w-4">{{ i + 1 }}.</span>
            <input v-model="item.descricao" class="input py-2.5 flex-1 min-w-0" placeholder="Ex: Polpa de Cupuaçu (1kg)" />
            <div class="relative w-32 shrink-0">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">R$</span>
              <input v-model.number="item.valor" type="number" min="0" step="0.01" class="input py-2.5 pl-9" />
            </div>
            <button type="button" class="p-2 text-slate-500 hover:text-red-500" :disabled="form.itens.length === 1" aria-label="Remover" @click="form.itens.splice(i, 1)">
              <Icon name="trash" class="w-4 h-4" />
            </button>
          </div>
        </div>
        <button type="button" class="mt-3 text-sm font-semibold text-nativo flex items-center gap-1 hover:underline" @click="form.itens.push({ descricao: '', valor: 0 })">
          <Icon name="plus" class="w-4 h-4" /> Adicionar Item
        </button>
      </div>

      <div>
        <div class="flex justify-between items-center mb-2">
          <label class="text-sm font-semibold text-slate-700">Margem de Lucro Desejada</label>
          <span class="text-xl font-bold text-nativo">{{ form.margem }}%</span>
        </div>
        <input v-model.number="form.margem" type="range" min="0" max="300" step="5" class="w-full accent-nativo" />
      </div>

      <div>
        <label class="label">Aplicar o preço sugerido a um produto (opcional)</label>
        <select v-model="form.product_id" class="input" @change="escolherProduto">
          <option :value="null">Não aplicar — apenas salvar o cálculo</option>
          <option v-for="p in produtos" :key="p.id" :value="p.id">{{ p.nome }}</option>
        </select>
      </div>

      <div class="grid grid-cols-3 gap-3 pt-2">
        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 text-center">
          <p class="text-xs font-semibold text-slate-600">Custo Total</p>
          <p class="text-lg font-bold text-slate-900">{{ moeda(custoTotal) }}</p>
        </div>
        <div class="rounded-xl bg-slate-50 border border-slate-100 p-3 text-center">
          <p class="text-xs font-semibold text-slate-600">Custo por unid.</p>
          <p class="text-lg font-bold text-red-600">{{ moeda(custoUnitario) }}</p>
        </div>
        <div class="rounded-xl bg-nativo-soft border border-nativo-light p-3 text-center">
          <p class="text-xs font-semibold text-nativo flex items-center justify-center gap-1"><Icon name="trending-up" class="w-3 h-3" /> Preço Sugerido</p>
          <p class="text-lg font-bold text-nativo">{{ moeda(precoSugerido) }}</p>
        </div>
      </div>
      <button class="btn-primary w-full py-4" :disabled="salvando" @click="salvar">
        <Icon v-if="salvando" name="loader" class="w-5 h-5" /> Salvar e Precificar
      </button>
    </div>
  </Modal>
</template>
