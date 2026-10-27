<script setup lang="ts">
/** Primeiro passo da compra: quantidade e contato. O pagamento acontece na tela do pedido. */
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { mascaraTelefone, moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'
import StepIndicator from '@/components/ui/StepIndicator.vue'

const props = defineProps<{ aberto: boolean; produto: { id: number; nome: string; preco: number; estoque: number } }>()
const emit = defineEmits<{ fechar: [] }>()
const router = useRouter()

const form = reactive({ quantidade: 1, nome: '', whatsapp: '' })
const enviando = ref(false)
const total = computed(() => props.produto.preco * form.quantidade)

function alterarQtd(delta: number) {
  form.quantidade = Math.min(Math.max(1, form.quantidade + delta), props.produto.estoque)
}

async function continuar() {
  enviando.value = true
  try {
    const pedido = await api<{ codigo: string }>('/api/v1/checkout', {
      method: 'POST', body: { product_id: props.produto.id, ...form },
    })
    emit('fechar')
    router.push(`/pedido/${pedido.codigo}`)
  } catch (e) {
    toast.erro(e)
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <Modal :aberto="aberto" titulo="Sua compra" icone="shopping-bag" @fechar="emit('fechar')">
    <StepIndicator :atual="1" />
    <form id="form-checkout" class="space-y-5" @submit.prevent="continuar">
      <div class="flex items-center justify-between gap-4 rounded-xl bg-slate-50 p-4">
        <div class="min-w-0">
          <p class="text-lg font-semibold text-slate-900">{{ produto.nome }}</p>
          <p class="text-sm text-slate-600">{{ moeda(produto.preco) }} cada</p>
        </div>
        <div class="shrink-0 text-center">
          <p class="text-sm font-semibold text-slate-700 mb-1">Quantidade</p>
          <div class="flex items-center gap-1" role="group" aria-label="Quantidade">
            <button type="button" class="w-12 h-12 rounded-xl border-2 border-slate-300 bg-white flex items-center justify-center disabled:opacity-40"
                    :disabled="form.quantidade <= 1" aria-label="Diminuir quantidade" @click="alterarQtd(-1)"><Icon name="minus" class="w-5 h-5" /></button>
            <span class="w-10 text-center text-2xl font-bold tabular-nums" aria-live="polite">{{ form.quantidade }}</span>
            <button type="button" class="w-12 h-12 rounded-xl border-2 border-slate-300 bg-white flex items-center justify-center disabled:opacity-40"
                    :disabled="form.quantidade >= produto.estoque" aria-label="Aumentar quantidade" @click="alterarQtd(1)"><Icon name="plus" class="w-5 h-5" /></button>
          </div>
        </div>
      </div>
      <div>
        <label class="label" for="ck-nome">Seu nome</label>
        <input id="ck-nome" v-model="form.nome" required minlength="2" maxlength="150" autocomplete="name" class="input" placeholder="Como o produtor vai te chamar" />
      </div>
      <div>
        <label class="label" for="ck-whats">WhatsApp</label>
        <input id="ck-whats" :value="form.whatsapp" required class="input" placeholder="(68) 9 9999-9999" inputmode="tel" autocomplete="tel"
               @input="form.whatsapp = mascaraTelefone(($event.target as HTMLInputElement).value)" />
        <p class="text-sm text-slate-600 mt-1.5">O produtor usa este número só para combinar a retirada com você.</p>
      </div>
      <div class="rounded-xl border border-nativo-light bg-nativo-soft p-4 text-slate-700 flex gap-3">
        <Icon name="map-pin" class="w-5 h-5 text-nativo shrink-0" />
        <p><strong class="text-nativo">Retirada no local.</strong> Depois do pagamento você combina dia e horário com o produtor pelo WhatsApp.</p>
      </div>
      <p class="text-sm text-slate-600">
        Ao continuar, você concorda com os <RouterLink to="/politicas/termos" target="_blank" class="text-nativo underline">Termos de Uso</RouterLink>
        e a <RouterLink to="/politicas/compras" target="_blank" class="text-nativo underline">Política de Compras e Cancelamentos</RouterLink>.
        Seu nome e WhatsApp são usados como explica a <RouterLink to="/politicas/privacidade" target="_blank" class="text-nativo underline">Política de Privacidade</RouterLink>.
      </p>
      <div class="flex items-center justify-between">
        <span class="text-lg font-semibold text-slate-700">Total a pagar</span>
        <span class="font-bold text-nativo text-3xl tabular-nums">{{ moeda(total) }}</span>
      </div>
    </form>
    <template #rodape>
      <button class="btn-ghost" @click="emit('fechar')">Voltar</button>
      <button type="submit" form="form-checkout" class="btn-primary flex-1 sm:flex-none text-lg" :disabled="enviando">
        <Icon :name="enviando ? 'loader' : 'arrow-right'" class="w-5 h-5" /> Continuar para o pagamento
      </button>
    </template>
  </Modal>
</template>
