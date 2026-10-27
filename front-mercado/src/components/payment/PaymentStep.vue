<script setup lang="ts">
/**
 * Etapa de pagamento reutilizável (pedido da vitrine e plano Premium).
 * Escolhe sozinha entre o formulário do Mercado Pago e o modo demonstração,
 * mostra o Pix pendente e acompanha a confirmação.
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import { api, ApiError } from '@/services/api'
import { toast } from '@/services/toast'
import PixPayment from '@/components/ui/PixPayment.vue'
import PaymentBrick from './PaymentBrick.vue'
import DemoPayment from './DemoPayment.vue'

export interface EstadoPagamento {
  status: string
  modo: 'simulado' | 'mercadopago'
  public_key: string | null
  gateway: string
  metodo: string | null
  pix_qr_code: string | null
  pix_qr_base64: string | null
}

const props = defineProps<{
  estado: EstadoPagamento
  valor: number
  base: string                     // ex.: /api/v1/checkout/CODIGO
  auth?: 'producer' | null
}>()
const emit = defineEmits<{ atualizado: [any] }>()

const enviando = ref(false)
let timer: number | undefined
const aguardandoPix = () => props.estado.status === 'aguardando_pagamento' && props.estado.metodo === 'pix' && !!props.estado.pix_qr_code

function pararConsulta() { if (timer) window.clearInterval(timer); timer = undefined }
function acompanhar() {
  pararConsulta()
  if (aguardandoPix() && props.estado.gateway === 'mercadopago') {
    timer = window.setInterval(async () => {
      try {
        const r = await api(props.base, { auth: props.auth ?? null })
        emit('atualizado', r)
        if (r.status !== 'aguardando_pagamento') pararConsulta()
      } catch { /* tenta de novo no próximo ciclo */ }
    }, 5000)
  }
}
watch(() => [props.estado.status, props.estado.pix_qr_code], acompanhar, { immediate: true })
onBeforeUnmount(pararConsulta)

async function enviarBrick(dados: any) {
  try {
    const r = await api(`${props.base}/pagar`, { method: 'POST', body: dados, auth: props.auth ?? null })
    emit('atualizado', r)
    if (r.status === 'pago') toast.sucesso('Pagamento aprovado!')
  } catch (e) {
    toast.erro(e)
    throw e  // o formulário do Mercado Pago volta a ficar disponível para tentar de novo
  }
}

async function pagarDemo(escolha: { metodo: string; parcelas: number }) {
  enviando.value = true
  try {
    const r = await api(`${props.base}/simular`, { method: 'POST', body: escolha, auth: props.auth ?? null })
    emit('atualizado', r)
    if (r.status === 'pago') toast.sucesso('Pagamento aprovado!')
  } catch (e) {
    toast.erro(e)
  } finally {
    enviando.value = false
  }
}

async function confirmarPixDemo() {
  enviando.value = true
  try {
    const r = await api(`${props.base}/simular/confirmar-pix`, { method: 'POST', auth: props.auth ?? null })
    emit('atualizado', r)
    toast.sucesso('Pix recebido!')
  } catch (e) {
    toast.erro(e instanceof ApiError ? e : String(e))
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <PixPayment v-if="aguardandoPix()" :valor="valor" :qr-code="estado.pix_qr_code" :qr-base64="estado.pix_qr_base64"
              :demonstracao="estado.gateway === 'simulado'" :carregando="enviando" @confirmar-demo="confirmarPixDemo" />
  <PaymentBrick v-else-if="estado.modo === 'mercadopago' && estado.public_key" :public-key="estado.public_key" :valor="valor" :enviar="enviarBrick" />
  <DemoPayment v-else :valor="valor" :carregando="enviando" @pagar="pagarDemo" />
</template>
