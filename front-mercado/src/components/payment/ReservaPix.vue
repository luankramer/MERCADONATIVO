<script setup lang="ts">
/**
 * Pix de reserva: usado quando o Mercado Pago está fora do ar.
 * O cliente paga um Pix Copia e Cola da conta do Mercado Nativo (com o valor exato e o número
 * do pedido) e avisa que pagou; a equipe confere no extrato e confirma o pedido.
 */
import { ref } from 'vue'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps<{ valor: number; qrCode?: string | null; informado?: boolean; carregando?: boolean }>()
const emit = defineEmits<{ gerar: []; paguei: [] }>()
const copiado = ref(false)

async function copiar() {
  try {
    await navigator.clipboard.writeText(props.qrCode || '')
    copiado.value = true
    toast.sucesso('Código Pix copiado! Abra o app do seu banco e cole em Pix Copia e Cola.')
    setTimeout(() => (copiado.value = false), 6000)
  } catch {
    toast.erro('Não foi possível copiar. Toque e segure no código para copiar.')
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-xl bg-amber-50 border border-amber-200 p-4 text-amber-900">
      <strong>O sistema de cartão está fora do ar agora.</strong>
      Você pode esperar alguns minutos e tentar de novo, ou pagar agora pelo <strong>Pix do Mercado Nativo</strong>:
      a nossa equipe confere e libera o seu pedido.
    </div>

    <button v-if="!qrCode" class="btn-primary w-full py-4 text-lg" :disabled="carregando" @click="emit('gerar')">
      <Icon :name="carregando ? 'loader' : 'qr'" class="w-6 h-6" /> Pagar com Pix do Mercado Nativo
    </button>

    <template v-else>
      <p class="text-center text-3xl font-bold text-nativo">{{ moeda(valor) }}</p>
      <div class="rounded-2xl border-2 border-nativo-light bg-nativo-soft p-4">
        <ol class="space-y-3 text-slate-700">
          <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">1</span><span class="pt-0.5">Toque em <strong>Copiar código Pix</strong>.</span></li>
          <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">2</span><span class="pt-0.5">No app do banco: <strong>Pix</strong> → <strong>Pix Copia e Cola</strong>. Confira o valor de <strong>{{ moeda(valor) }}</strong> e o recebedor <strong>Mercado Nativo</strong>.</span></li>
          <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">3</span><span class="pt-0.5">Volte aqui e toque em <strong>Já paguei</strong>. A equipe confirma e você recebe o aviso no WhatsApp.</span></li>
        </ol>
        <button class="btn-primary w-full mt-4 py-4 text-lg" @click="copiar">
          <Icon :name="copiado ? 'check' : 'copy'" class="w-6 h-6" /> {{ copiado ? 'Código copiado!' : 'Copiar código Pix' }}
        </button>
        <p class="font-mono text-xs leading-relaxed text-slate-600 break-all line-clamp-2 select-all mt-3" aria-label="Código Pix">{{ qrCode }}</p>
      </div>
      <div v-if="informado" class="rounded-xl bg-sky-50 border border-sky-200 p-4 text-sky-900 text-center">
        <Icon name="check" class="w-6 h-6 mx-auto mb-1" />
        Recebemos o seu aviso. Assim que a equipe conferir o Pix, o pedido é liberado e você recebe o aviso no WhatsApp.
      </div>
      <button v-else class="btn-outline w-full py-4 text-lg" :disabled="carregando" @click="emit('paguei')">
        <Icon :name="carregando ? 'loader' : 'check'" class="w-5 h-5" /> Já paguei
      </button>
    </template>
  </div>
</template>
