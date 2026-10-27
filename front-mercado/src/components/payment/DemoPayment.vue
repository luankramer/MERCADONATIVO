<script setup lang="ts">
/** Pagamento de demonstração (PAYMENT_MODE=simulado): mostra o fluxo sem cobrar nada. */
import { computed, ref } from 'vue'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps<{ valor: number; carregando?: boolean }>()
const emit = defineEmits<{ pagar: [{ metodo: 'pix' | 'credit_card' | 'debit_card'; parcelas: number }] }>()

const metodo = ref<'pix' | 'credit_card' | 'debit_card'>('pix')
const parcelas = ref(1)
const opcoes = [
  { id: 'pix', nome: 'Pix', icone: 'qr', detalhe: 'Na hora' },
  { id: 'credit_card', nome: 'Crédito', icone: 'credit-card', detalhe: 'Até 6x' },
  { id: 'debit_card', nome: 'Débito', icone: 'credit-card', detalhe: 'À vista' },
] as const
const valorParcela = computed(() => props.valor / parcelas.value)
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Forma de pagamento">
      <button v-for="o in opcoes" :key="o.id" type="button" role="radio" :aria-checked="metodo === o.id"
              :class="['rounded-xl border-2 p-3 text-center transition min-h-[96px]',
                       metodo === o.id ? 'border-nativo bg-nativo-soft text-nativo ring-2 ring-nativo-light' : 'border-slate-300 text-slate-700 hover:border-nativo']"
              @click="metodo = o.id; parcelas = 1">
        <Icon :name="o.icone" class="w-7 h-7 mx-auto" />
        <span class="block text-lg font-bold mt-1">{{ o.nome }}</span>
        <span class="block text-xs text-slate-600">{{ o.detalhe }}</span>
      </button>
    </div>

    <div v-if="metodo !== 'pix'" class="rounded-2xl bg-gradient-to-br from-slate-800 to-slate-950 text-white p-5 shadow-lg">
      <div class="flex justify-between text-xs text-white/70"><span>{{ metodo === 'credit_card' ? 'Crédito' : 'Débito' }}</span><span>Cartão de teste</span></div>
      <p class="font-mono text-lg tracking-widest mt-6">5031 •••• •••• 6351</p>
      <div class="flex justify-between text-xs text-white/70 mt-4"><span>CLIENTE TESTE</span><span>11/30</span></div>
    </div>
    <div v-if="metodo === 'credit_card'">
      <label class="label">Parcelas</label>
      <select v-model.number="parcelas" class="input">
        <option v-for="n in 6" :key="n" :value="n">{{ n }}x de {{ moeda(valor / n) }}{{ n === 1 ? ' (à vista)' : ' sem juros' }}</option>
      </select>
    </div>

    <p class="rounded-xl bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
      <strong>Modo demonstração:</strong> nenhum valor é cobrado. Para receber de verdade, ative o Mercado Pago no arquivo <code>.env</code>.
    </p>
    <button class="btn-primary w-full py-4 text-lg" :disabled="carregando" @click="emit('pagar', { metodo, parcelas })">
      <Icon :name="carregando ? 'loader' : 'lock'" class="w-5 h-5" />
      {{ metodo === 'pix' ? 'Gerar Pix' : parcelas > 1 ? `Pagar ${parcelas}x de ${moeda(valorParcela)}` : `Pagar ${moeda(valor)}` }}
    </button>
  </div>
</template>
