<script setup lang="ts">
/** Assinatura do plano Premium (crédito, débito ou Pix). */
import { ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'
import PaymentStep from '@/components/payment/PaymentStep.vue'

const props = defineProps<{ aberto: boolean }>()
const emit = defineEmits<{ fechar: []; ativado: [] }>()

const preco = ref(9.9)
const assinatura = ref<any>(null)
const carregando = ref(false)

watch(() => props.aberto, async (v) => {
  if (!v) return
  assinatura.value = null
  try { preco.value = (await api('/api/v1/checkout/config')).preco_premium } catch { /* mantém o padrão */ }
})

async function comecar() {
  carregando.value = true
  try {
    assinatura.value = await api('/api/v1/producers/me/premium', { method: 'POST', auth: 'producer' })
  } catch (e) {
    toast.erro(e)
  } finally {
    carregando.value = false
  }
}

function atualizar(novo: any) {
  assinatura.value = novo
  if (novo.status === 'pago') {
    toast.sucesso('Plano Premium ativado. Bom proveito!')
    emit('ativado')
    emit('fechar')
  }
}
</script>

<template>
  <Modal :aberto="aberto" titulo="Plano Premium" icone="star" tom="terra" @fechar="emit('fechar')">
    <div v-if="!assinatura" class="space-y-5">
      <p class="text-3xl font-bold text-slate-900 tabular-nums">{{ moeda(preco) }}<span class="text-base font-medium text-slate-600"> / mês</span></p>
      <ul class="space-y-3 text-sm text-slate-700">
        <li class="flex gap-2.5"><Icon name="check-circle" class="w-5 h-5 text-nativo shrink-0" /> Seus produtos com selo <strong>Destaque</strong> no topo da vitrine</li>
        <li class="flex gap-2.5"><Icon name="check-circle" class="w-5 h-5 text-nativo shrink-0" /> <strong>Calculadora de Custos</strong> para acertar o preço</li>
        <li class="flex gap-2.5"><Icon name="check-circle" class="w-5 h-5 text-nativo shrink-0" /> Métricas de visitas e vendas de cada produto</li>
      </ul>
      <button class="btn-primary w-full py-4" :disabled="carregando" @click="comecar">
        <Icon :name="carregando ? 'loader' : 'lock'" class="w-5 h-5" /> Assinar agora
      </button>
      <p class="text-xs text-slate-500 text-center">Pague com cartão de crédito, débito ou Pix. Sem fidelidade.</p>
    </div>
    <PaymentStep v-else :estado="assinatura" :valor="assinatura.valor" :base="`/api/v1/producers/me/premium/${assinatura.codigo}`"
                 auth="producer" @atualizado="atualizar" />
  </Modal>
</template>
