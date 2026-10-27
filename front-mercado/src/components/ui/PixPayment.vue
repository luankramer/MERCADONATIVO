<script setup lang="ts">
/** QR Code PIX + "copia e cola". */
import { ref } from 'vue'
import { toast } from '@/services/toast'
import { moeda } from '@/utils/format'
import Icon from './Icon.vue'

const props = defineProps<{ valor: number; qrCode?: string | null; qrBase64?: string | null; demonstracao?: boolean; carregando?: boolean }>()
const emit = defineEmits<{ confirmarDemo: [] }>()
const copiado = ref(false)

async function copiar() {
  try {
    await navigator.clipboard.writeText(props.qrCode || '')
    copiado.value = true
    toast.sucesso('Código Pix copiado! Agora abra o app do seu banco e cole em Pix Copia e Cola.')
    setTimeout(() => (copiado.value = false), 6000)
  } catch {
    toast.erro('Não foi possível copiar. Toque e segure no código para copiar.')
  }
}
</script>

<template>
  <div class="space-y-5">
    <p class="text-center text-3xl font-bold text-nativo">{{ moeda(valor) }}</p>

    <!-- Pagando pelo próprio celular: copia e cola (o caminho mais simples) -->
    <div v-if="qrCode" class="rounded-2xl border-2 border-nativo-light bg-nativo-soft p-4">
      <h3 class="text-lg font-bold text-slate-900">Como pagar com Pix</h3>
      <ol class="mt-3 space-y-3 text-slate-700">
        <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">1</span><span class="pt-0.5">Toque em <strong>Copiar código Pix</strong>.</span></li>
        <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">2</span><span class="pt-0.5">Abra o aplicativo do seu banco e escolha <strong>Pix</strong> → <strong>Pix Copia e Cola</strong>.</span></li>
        <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">3</span><span class="pt-0.5">Cole o código, confira o valor de <strong>{{ moeda(valor) }}</strong> e confirme.</span></li>
        <li class="flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-nativo text-white font-bold flex items-center justify-center">4</span><span class="pt-0.5">Volte para esta tela. Ela atualiza sozinha quando o banco confirmar.</span></li>
      </ol>
      <button class="btn-primary w-full mt-4 py-4 text-lg" @click="copiar">
        <Icon :name="copiado ? 'check' : 'copy'" class="w-6 h-6" /> {{ copiado ? 'Código copiado!' : 'Copiar código Pix' }}
      </button>
      <p class="font-mono text-xs leading-relaxed text-slate-600 break-all line-clamp-2 select-all mt-3" aria-label="Código Pix">{{ qrCode }}</p>
    </div>

    <!-- Pagando com outro celular: lê o QR Code -->
    <details class="rounded-2xl border border-slate-200 bg-white p-4" :open="!qrCode">
      <summary class="cursor-pointer font-semibold text-slate-800 min-h-[32px]">Vai pagar com outro celular? Mostrar o QR Code</summary>
      <p class="text-slate-600 mt-2">No app do banco, escolha <strong>Pix → Ler QR Code</strong> e aponte a câmera para o quadrado abaixo.</p>
      <div class="mx-auto mt-3 w-56 h-56 rounded-2xl border border-slate-200 bg-white p-3 flex items-center justify-center">
        <img v-if="qrBase64" :src="`data:image/png;base64,${qrBase64}`" alt="QR Code do Pix" class="w-full h-full object-contain" />
        <div v-else class="flex flex-col items-center gap-2 text-slate-600">
          <Icon name="qr" class="w-24 h-24 text-slate-800" :stroke="1.25" />
          <span v-if="demonstracao" class="text-sm font-semibold">Exemplo</span>
        </div>
      </div>
    </details>

    <div v-if="demonstracao" class="rounded-xl bg-amber-50 border border-amber-200 p-4 text-amber-900">
      <strong>Demonstração:</strong> este Pix não cobra nada. Toque abaixo para simular a confirmação do banco.
      <button class="btn w-full mt-3 bg-amber-600 hover:bg-amber-700 text-white py-3" :disabled="carregando" @click="emit('confirmarDemo')">
        <Icon :name="carregando ? 'loader' : 'check'" class="w-5 h-5" /> Simular Pix recebido
      </button>
    </div>
    <p v-else class="text-slate-600 flex items-center justify-center gap-2" aria-live="polite">
      <Icon name="loader" class="w-5 h-5" /> Esperando o banco confirmar o pagamento...
    </p>
  </div>
</template>
