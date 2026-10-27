<script setup lang="ts">
/** Pedido: pagamento (crédito, débito ou Pix), confirmação e como retirar. */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
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
            <p class="text-xl font-semibold text-slate-900">Pagamento cancelado</p>
            <p class="text-slate-600 mt-1">Nenhum valor foi cobrado.</p>
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

            <p class="flex items-center justify-center gap-2 text-center text-slate-600 px-2">
              <Icon name="sprout" class="w-5 h-5 text-nativo shrink-0" /> Sua compra ajuda diretamente quem produz na sua região.
            </p>
          </section>
        </template>
      </div>
    </main>
  </div>
</template>
