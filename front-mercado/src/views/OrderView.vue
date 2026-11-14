<script setup lang="ts">
/** Pedido: pagamento (crédito, débito ou Pix), confirmação e como retirar. */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmar } from '@/services/confirm'
import { dataHora, moeda } from '@/utils/format'
import { linkWhatsappSac, temSac } from '@/utils/suporte'
import Icon from '@/components/ui/Icon.vue'
import SiteRodape from '@/components/ui/SiteRodape.vue'
import PaymentStep from '@/components/payment/PaymentStep.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import StepIndicator from '@/components/ui/StepIndicator.vue'

const route = useRoute()
const pedido = ref<any>(null)
const naoEncontrado = ref(false)
const passo = computed(() => (pedido.value?.status === 'aguardando_pagamento' ? 2 : 3))

onMounted(async () => {
  try {
    pedido.value = await api(`/api/v1/checkout/${route.params.codigo}`)
  } catch (e: any) {
    if (e.status === 404) naoEncontrado.value = true
    else toast.erro(e)
  }
})

// ---- Cancelamento (antes da retirada) ----
const finalWhats = ref('')
const motivoCancelamento = ref('')
const cancelando = ref(false)
// Só "approved" é devolução concluída; "pending" está no Mercado Pago, "manual" é Pix devolvido pela equipe
const devolvido = computed(() => ['approved', 'simulado'].includes(pedido.value?.reembolso_status))
const QUEM: Record<string, string> = { cliente: 'por você', produtor: 'pelo produtor', admin: 'pela equipe do Mercado Nativo',
  mercadopago: 'no Mercado Pago', sistema: 'pelo Mercado Nativo (o produto saiu da vitrine)' }
const textoDevolucao = computed(() => {
  const m = pedido.value?.metodo
  if (m === 'pix') return 'O dinheiro volta para a conta que pagou o Pix, normalmente em poucos minutos.'
  if (m === 'credit_card' || m === 'debit_card') return 'O estorno aparece no cartão conforme o prazo do seu banco (no crédito, pode levar até 2 faturas).'
  return 'O valor volta pela mesma forma de pagamento.'
})
const tituloCancelado = computed(() => {
  const s = pedido.value?.reembolso_status
  if (devolvido.value) return 'Pedido cancelado e dinheiro devolvido'
  if (s === 'pending' || s === 'manual') return 'Pedido cancelado · devolução em andamento'
  return 'Pedido cancelado'
})
const situacaoDevolucao = computed(() => {
  const valor = moeda(pedido.value?.valor_total ?? 0)
  switch (pedido.value?.reembolso_status) {
    case 'approved': case 'simulado': return `Valor devolvido: ${valor}. ${textoDevolucao.value}`
    case 'pending': return `A devolução de ${valor} já foi pedida ao Mercado Pago e está sendo processada. ${textoDevolucao.value}`
    case 'manual': return `A equipe do Mercado Nativo devolve ${valor} pelo Pix em até 2 dias úteis.`
    case 'falhou': return 'Houve um problema na devolução pelo Mercado Pago. A nossa equipe já foi avisada e vai falar com você.'
    default: return 'Nenhum valor foi cobrado.'
  }
})
const linkSacPedido = computed(() =>
  linkWhatsappSac(`Olá! Quero falar sobre o cancelamento do pedido nº ${pedido.value?.numero} (${pedido.value?.quantidade}x ${pedido.value?.produto}).`))
// Pago (ou retirado nos 7 dias): o cliente PEDE e a equipe confere com o produtor antes de devolver
const pedePelaEquipe = computed(() => !pedido.value?.pode_cancelar && pedido.value?.pode_solicitar_cancelamento)
const solicitacao = computed(() => pedido.value?.status !== 'cancelado' ? pedido.value?.solicitacao : null)
const textoCancelar = computed(() => {
  const p = pedido.value
  if (!pedePelaEquipe.value) return 'Você ainda não pagou. Se cancelar, nada será cobrado.'
  if (p?.status === 'retirado')
    return `Você ainda está no prazo de 7 dias para desistir (até ${dataHora(p.prazo_arrependimento)}). Peça o cancelamento: a equipe do Mercado Nativo combina com você e com o produtor a devolução do produto e do dinheiro.`
  return `Como o pedido já foi pago, a equipe do Mercado Nativo confirma com o produtor se o produto ainda não foi entregue ou enviado. Se for aprovado, a devolução é automática. ${textoDevolucao.value}`
})

async function cancelarPedido() {
  const pede = pedePelaEquipe.value
  if (!(await confirmar({
    titulo: pede ? 'Pedir o cancelamento?' : 'Cancelar este pedido?',
    texto: pede
      ? 'A equipe do Mercado Nativo vai confirmar com o produtor e te responder pelo WhatsApp.'
      : 'Nada foi cobrado. O pedido será encerrado.',
    sim: pede ? 'Sim, pedir o cancelamento' : 'Sim, cancelar', nao: 'Não, manter o pedido', perigo: true,
  }))) return
  cancelando.value = true
  try {
    pedido.value = await api(`/api/v1/checkout/${pedido.value.codigo}/cancelar`, {
      method: 'POST', body: { whatsapp_final: finalWhats.value, motivo: motivoCancelamento.value.trim() || null },
    })
    toast.sucesso(pede ? 'Pedido de cancelamento enviado. A equipe vai responder pelo WhatsApp.' : 'Pedido cancelado.')
  } catch (e) {
    toast.erro(e)
  } finally {
    cancelando.value = false
  }
}

async function copiarLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.sucesso('Link do pedido copiado. Guarde no WhatsApp ou nas notas do celular.')
  } catch {
    toast.erro('Não foi possível copiar. Salve esta página nos favoritos do navegador.')
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <PublicHeader />
    <main class="px-4 pt-4 pb-12 flex justify-center">
      <div class="w-full max-w-lg">
        <RouterLink to="/" class="back-link mb-3"><Icon name="arrow-left" class="w-5 h-5" /> Continuar comprando</RouterLink>

        <div v-if="naoEncontrado" class="card p-8 text-center">
          <Icon name="search" class="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <p class="font-serif text-2xl font-bold text-slate-900">Pedido não encontrado</p>
          <p class="text-slate-600 mt-1">Confira se o link está completo.</p>
        </div>
        <div v-else-if="!pedido" class="card h-96 animate-pulse" />

        <template v-else>
          <StepIndicator v-if="pedido.status !== 'cancelado'" :atual="passo" />

          <!-- Resumo -->
          <section class="card p-5 mb-4">
            <p class="text-sm text-slate-600">Pedido nº {{ pedido.numero }}</p>
            <h1 class="font-serif text-2xl font-bold text-slate-900 leading-snug">{{ pedido.quantidade }}× {{ pedido.produto }}</h1>
            <p class="text-slate-700 flex items-center gap-1.5 mt-1">
              <Icon name="map-pin" class="w-5 h-5 shrink-0 text-nativo" /> {{ pedido.produtor?.nome_loja }} · {{ pedido.produtor?.cidade }}, {{ pedido.produtor?.estado }}
            </p>
            <p class="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
              <span class="text-lg font-semibold text-slate-700">Total</span>
              <span class="text-3xl font-bold text-nativo tabular-nums">{{ moeda(pedido.valor_total) }}</span>
            </p>
          </section>

          <!-- Pagamento -->
          <section v-if="pedido.status === 'aguardando_pagamento'" class="card p-5">
            <h2 class="text-xl font-bold text-slate-900 mb-4">Como você quer pagar?</h2>
            <PaymentStep :estado="pedido" :valor="pedido.valor_total" :base="`/api/v1/checkout/${pedido.codigo}`" @atualizado="pedido = $event" />
          </section>

          <section v-else-if="pedido.status === 'cancelado'" class="card p-6 text-center">
            <Icon name="alert" class="w-12 h-12 text-red-500 mx-auto mb-2" />
            <p class="text-xl font-semibold text-slate-900">{{ tituloCancelado }}</p>
            <p v-if="pedido.cancelado_em" class="text-slate-600 mt-1">
              Cancelado {{ QUEM[pedido.cancelado_por] || '' }} em {{ dataHora(pedido.cancelado_em) }}.
            </p>
            <p v-if="pedido.motivo_cancelamento" class="text-slate-600 mt-1">Motivo: {{ pedido.motivo_cancelamento }}</p>
            <p class="text-slate-700 mt-3">{{ situacaoDevolucao }}</p>
            <RouterLink v-if="pedido.product_id" :to="`/vitrine/produto/${pedido.product_id}`" class="btn-outline mt-4">Fazer um novo pedido</RouterLink>
          </section>

          <!-- Confirmado: o que fazer agora -->
          <section v-else class="space-y-4">
            <div class="rounded-3xl bg-nativo text-white p-6 text-center">
              <div class="w-20 h-20 mx-auto rounded-full bg-white text-nativo flex items-center justify-center">
                <Icon name="check" class="w-11 h-11" :stroke="3" />
              </div>
              <p class="font-serif text-3xl font-bold mt-4">
                {{ pedido.status === 'retirado' ? 'Pedido entregue' : 'Pagamento recebido!' }}
              </p>
              <p class="text-lg text-white/90 mt-2">
                {{ pedido.status === 'retirado' ? `Obrigado pela compra, ${pedido.cliente}!` : `Tudo certo, ${pedido.cliente}.` }}
                Pago{{ pedido.metodo_nome ? ` com ${pedido.metodo_nome}` : '' }}{{ pedido.parcelas > 1 ? ` em ${pedido.parcelas}x` : '' }}.
              </p>
            </div>

            <div v-if="pedido.status !== 'retirado'" class="card p-5">
              <h2 class="text-xl font-bold text-slate-900">Como retirar o seu produto</h2>
              <ol class="mt-4 space-y-4">
                <li class="flex gap-3">
                  <span class="w-9 h-9 shrink-0 rounded-full bg-nativo-light text-nativo font-bold flex items-center justify-center">1</span>
                  <span class="text-slate-700 pt-1">Toque no botão verde abaixo para conversar com <strong>{{ pedido.produtor?.nome_loja }}</strong> no WhatsApp.</span>
                </li>
                <li class="flex gap-3">
                  <span class="w-9 h-9 shrink-0 rounded-full bg-nativo-light text-nativo font-bold flex items-center justify-center">2</span>
                  <span class="text-slate-700 pt-1">Combine o dia e o horário da retirada.</span>
                </li>
                <li class="flex gap-3">
                  <span class="w-9 h-9 shrink-0 rounded-full bg-nativo-light text-nativo font-bold flex items-center justify-center">3</span>
                  <span class="text-slate-700 pt-1">
                    Vá até o produtor em <strong>{{ pedido.produtor?.cidade }}</strong>{{ pedido.produtor?.endereco ? ` (${pedido.produtor.endereco})` : '' }}
                    e informe o pedido nº <strong>{{ pedido.numero }}</strong>.
                  </span>
                </li>
              </ol>
              <a v-if="pedido.whatsapp_link" :href="pedido.whatsapp_link" target="_blank" rel="noopener" class="btn-primary w-full py-4 text-lg mt-5">
                <Icon name="phone" class="w-6 h-6" /> Combinar a retirada pelo WhatsApp
              </a>
            </div>

            <button type="button" class="btn-ghost w-full" @click="copiarLink"><Icon name="copy" class="w-5 h-5" /> Guardar o link deste pedido</button>

            <!-- Pedido de cancelamento: a equipe confere com o produtor -->
            <div v-if="solicitacao?.status === 'pendente'" class="rounded-2xl border-2 border-amber-300 bg-amber-50 p-5" role="status">
              <h2 class="text-lg font-bold text-amber-900 flex items-center gap-2"><Icon name="clock" class="w-5 h-5" /> Pedido de cancelamento enviado</h2>
              <p class="text-amber-900 mt-1">
                Recebemos em {{ dataHora(solicitacao.em) }}. A equipe do Mercado Nativo vai confirmar com o produtor se o produto
                ainda não foi entregue ou enviado e te responde pelo WhatsApp. Se for aprovado, a devolução é automática. {{ textoDevolucao }}
              </p>
            </div>
            <div v-else-if="solicitacao?.status === 'recusada'" class="card p-5" role="status">
              <h2 class="text-lg font-bold text-slate-900">Pedido de cancelamento não aprovado</h2>
              <p v-if="solicitacao.resposta" class="text-slate-700 mt-1">Motivo: {{ solicitacao.resposta }}</p>
              <p class="text-slate-700 mt-1">Se tiver dúvida, fale com o SAC do Mercado Nativo informando o pedido nº {{ pedido.numero }}.</p>
              <a v-if="linkSacPedido" :href="linkSacPedido" target="_blank" rel="noopener" class="btn-outline w-full mt-4"><Icon name="message" class="w-5 h-5" /> Falar com o SAC pelo WhatsApp</a>
              <a v-else-if="temSac" href="#sac" class="btn-outline w-full mt-4">Ver os contatos do SAC</a>
            </div>

            <p class="flex items-center justify-center gap-2 text-center text-slate-600 px-2">
              <Icon name="sprout" class="w-5 h-5 text-nativo shrink-0" /> Sua compra ajuda diretamente quem produz na sua região.
            </p>
          </section>
          <details v-if="pedido.pode_cancelar || pedido.pode_solicitar_cancelamento" class="card p-5 mt-4">
            <summary class="cursor-pointer text-lg font-semibold text-slate-800 min-h-[32px]">Quero cancelar este pedido</summary>
            <p class="text-slate-700 mt-3">{{ textoCancelar }}</p>
            <label class="label mt-4" for="cancel-whats">Para confirmar que é você, digite os 4 últimos números do seu WhatsApp</label>
            <input id="cancel-whats" v-model="finalWhats" inputmode="numeric" maxlength="4" autocomplete="off"
                   class="input text-2xl tracking-[0.5em] w-40" placeholder="0000"
                   @input="finalWhats = finalWhats.replace(/\D/g, '').slice(0, 4)" />
            <label class="label mt-4" for="cancel-motivo">Por que vai cancelar? (opcional)</label>
            <input id="cancel-motivo" v-model="motivoCancelamento" maxlength="300" class="input" placeholder="Ex.: não vou conseguir buscar" />
            <button type="button" class="btn w-full py-4 mt-4 bg-red-600 text-white hover:bg-red-700 text-lg"
                    :disabled="finalWhats.length !== 4 || cancelando" @click="cancelarPedido">
              <Icon :name="cancelando ? 'loader' : 'x'" class="w-5 h-5" />
              {{ pedePelaEquipe ? 'Pedir o cancelamento' : 'Cancelar o pedido' }}
            </button>
          </details>
        </template>
        <SiteRodape empilhado :mensagem="pedido ? `Olá! Preciso de ajuda com o pedido nº ${pedido.numero} no Mercado Nativo.` : undefined" />
      </div>
    </main>
  </div>
</template>
