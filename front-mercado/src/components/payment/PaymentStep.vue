<script setup lang="ts">
/**
 * Etapa de pagamento reutilizável (pedido da vitrine e plano Premium).
 * Escolhe sozinha entre o formulário do Mercado Pago, o Pix de reserva (quando o Mercado Pago
 * está fora do ar) e o modo demonstração; mostra o Pix pendente e acompanha a confirmação.
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import { api, ApiError } from '@/services/api'
import { toast } from '@/services/toast'
import PixPayment from '@/components/ui/PixPayment.vue'
import Icon from '@/components/ui/Icon.vue'
import PaymentBrick from './PaymentBrick.vue'
import DemoPayment from './DemoPayment.vue'
import ReservaPix from './ReservaPix.vue'

export interface EstadoPagamento {
  status: string
  modo: 'simulado' | 'mercadopago' | 'desativado'
  public_key: string | null
  gateway: string
  metodo: string | null
  pix_qr_code: string | null
  pix_qr_base64: string | null
  mp_disponivel?: boolean
  pix_reserva?: boolean
  reserva_informado?: boolean
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
const aguardando = () => props.estado.status === 'aguardando_pagamento'
const aguardandoPix = () => aguardando() && props.estado.metodo === 'pix' && !!props.estado.pix_qr_code
const naReserva = () => aguardando() && props.estado.gateway === 'manual'

function pararConsulta() { if (timer) window.clearInterval(timer); timer = undefined }
function acompanhar() {
  pararConsulta()
  // Pix do Mercado Pago: confere a cada 5 s. Pix de reserva já avisado: a cada 20 s (a equipe confirma)
  const intervalo = naReserva() ? (props.estado.reserva_informado ? 20000 : 0)
    : (aguardandoPix() && props.estado.gateway === 'mercadopago' ? 5000 : 0)
  if (!intervalo) return
  timer = window.setInterval(async () => {
    try {
      const r = await api(props.base, { auth: props.auth ?? null })
      emit('atualizado', r)
      if (r.status !== 'aguardando_pagamento') pararConsulta()
    } catch { /* tenta de novo no próximo ciclo */ }
  }, intervalo)
}
watch(() => [props.estado.status, props.estado.pix_qr_code, props.estado.reserva_informado], acompanhar, { immediate: true })
onBeforeUnmount(pararConsulta)

async function atualizar() {
  try { emit('atualizado', await api(props.base, { auth: props.auth ?? null })) } catch { /* mantém a tela */ }
}

async function enviarBrick(dados: any) {
  try {
    const r = await api(`${props.base}/pagar`, { method: 'POST', body: dados, auth: props.auth ?? null })
    emit('atualizado', r)
    if (r.status === 'pago') toast.sucesso('Pagamento aprovado!')
  } catch (e) {
    toast.erro(e)
    // Mercado Pago fora do ar: recarrega o pedido para mostrar o Pix de reserva (se houver)
    if (e instanceof ApiError && e.status === 503) await atualizar()
    throw e  // o formulário do Mercado Pago volta a ficar disponível para tentar de novo
  }
}

async function acaoReserva(caminho: string, mensagem: string) {
  enviando.value = true
  try {
    const r = await api(`${props.base}/${caminho}`, { method: 'POST', auth: props.auth ?? null })
    emit('atualizado', r)
    if (mensagem) toast.sucesso(mensagem)
  } catch (e) {
    toast.erro(e)
  } finally {
    enviando.value = false
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
  <ReservaPix v-if="naReserva()" :valor="valor" :qr-code="estado.pix_qr_code" :informado="estado.reserva_informado"
              :carregando="enviando" @paguei="acaoReserva('pix-reserva/paguei', 'Obrigado! A equipe vai conferir o seu Pix.')" />
  <PixPayment v-else-if="aguardandoPix()" :valor="valor" :qr-code="estado.pix_qr_code" :qr-base64="estado.pix_qr_base64"
              :demonstracao="estado.gateway === 'simulado'" :carregando="enviando" @confirmar-demo="confirmarPixDemo" />
  <ReservaPix v-else-if="estado.pix_reserva" :valor="valor" :carregando="enviando"
              @gerar="acaoReserva('pix-reserva', '')" />
  <PaymentBrick v-else-if="estado.modo === 'mercadopago' && estado.public_key" :public-key="estado.public_key" :valor="valor" :enviar="enviarBrick" />
  <DemoPayment v-else-if="estado.modo === 'simulado'" :valor="valor" :carregando="enviando" @pagar="pagarDemo" />
  <div v-else class="rounded-xl bg-amber-50 border border-amber-200 p-5 text-amber-900 text-center space-y-3">
    <Icon name="alert" class="w-8 h-8 mx-auto" />
    <p><strong>Os pagamentos estão temporariamente indisponíveis.</strong> Nada foi cobrado. Tente de novo em alguns minutos.</p>
    <button class="btn-outline" @click="atualizar">Tentar de novo</button>
  </div>
</template>
