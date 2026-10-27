<script setup lang="ts">
/**
 * Formulário oficial do Mercado Pago (Payment Brick): crédito, débito e Pix.
 * Os dados do cartão são digitados em campos seguros do próprio Mercado Pago e viram um token;
 * o nosso sistema nunca vê o número do cartão.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps<{ publicKey: string; valor: number; enviar: (dados: any) => Promise<void> }>()

const carregando = ref(true)
const erro = ref<string | null>(null)
const idContainer = `brick-${Math.random().toString(36).slice(2)}`
let controller: any = null

function carregarSdk(): Promise<any> {
  const w = window as any
  if (w.MercadoPago) return Promise.resolve(w.MercadoPago)
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://sdk.mercadopago.com/js/v2'
    script.async = true
    script.onload = () => resolve(w.MercadoPago)
    script.onerror = () => reject(new Error('Não foi possível carregar o Mercado Pago. Verifique sua internet.'))
    document.head.appendChild(script)
  })
}

async function montar() {
  carregando.value = true
  erro.value = null
  try {
    const MercadoPago = await carregarSdk()
    const mp = new MercadoPago(props.publicKey, { locale: 'pt-BR' })
    controller = await mp.bricks().create('payment', idContainer, {
      initialization: { amount: Number(props.valor.toFixed(2)) },
      customization: {
        paymentMethods: { creditCard: 'all', debitCard: 'all', bankTransfer: 'all', maxInstallments: 6 },
        visual: {
          style: { theme: 'default', customVariables: { baseColor: '#0B6B4A', borderRadiusMedium: '12px', borderRadiusLarge: '16px' } },
          hideFormTitle: true,
        },
      },
      callbacks: {
        onReady: () => { carregando.value = false },
        onSubmit: ({ formData }: { formData: any }) => props.enviar(formData),
        onError: (e: any) => {
          console.error('Mercado Pago', e)
          if (e?.type === 'critical') erro.value = 'O formulário de pagamento não abriu. Tente novamente.'
        },
      },
    })
  } catch (e) {
    carregando.value = false
    erro.value = e instanceof Error ? e.message : 'Falha ao abrir o pagamento.'
  }
}

onMounted(montar)
onBeforeUnmount(() => { try { controller?.unmount() } catch { /* já desmontado */ } })
</script>

<template>
  <div>
    <div v-if="carregando && !erro" class="space-y-3 py-2" aria-busy="true">
      <div v-for="i in 3" :key="i" class="h-14 rounded-xl bg-slate-100 animate-pulse" />
    </div>
    <div v-if="erro" class="rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-700 text-center">
      {{ erro }}
      <button class="btn-ghost w-full mt-3" @click="montar"><Icon name="refresh" class="w-4 h-4" /> Tentar de novo</button>
    </div>
    <div :id="idContainer" />
    <p class="mt-3 text-xs text-slate-500 flex items-center justify-center gap-1.5">
      <Icon name="lock" class="w-3.5 h-3.5" /> Pagamento processado pelo Mercado Pago. Não guardamos dados do seu cartão.
    </p>
  </div>
</template>
