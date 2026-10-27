<script setup lang="ts">
/** "Analisar Publicação": dados do produto + análise automática da IA + aprovar/rejeitar. */
import { computed, ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmarComMotivo } from '@/services/confirm'
import { moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'
import Modal from '@/components/ui/Modal.vue'

const props = defineProps<{ productId: number | null }>()
const emit = defineEmits<{ fechar: []; alterado: [] }>()

const produto = ref<any>(null)
const rejeitando = ref(false)
const motivo = ref('')
const enviando = ref(false)
const fotoAtual = ref(0)

const analise = computed(() => produto.value?.analise_ia)
const corAnalise = computed(() => {
  const s = analise.value?.score ?? 0
  if (analise.value?.negativas?.length || s < 40) return 'border-red-200 bg-red-50 text-red-800'
  if (s < 70) return 'border-amber-200 bg-amber-50 text-amber-800'
  return 'border-emerald-200 bg-emerald-50 text-emerald-800'
})

watch(() => props.productId, async (id) => {
  produto.value = null
  rejeitando.value = false
  motivo.value = ''
  fotoAtual.value = 0
  if (!id) return
  try { produto.value = await api(`/api/v1/admin/products/${id}`, { auth: 'admin' }) } catch (e) { toast.erro(e); emit('fechar') }
}, { immediate: true })

async function excluir() {
  const motivo = await confirmarComMotivo({
    titulo: `Excluir "${produto.value?.nome}"?`,
    texto: 'A publicação sai da vitrine para sempre, com fotos e avaliações.',
    motivo: { rotulo: 'Motivo (o vendedor recebe pelo WhatsApp)', placeholder: 'Ex.: produto proibido pelas Regras para Vendedores' },
    sim: 'Sim, excluir publicação', nao: 'Não, manter', perigo: true,
  })
  if (motivo === null) return
  enviando.value = true
  try {
    const r = await api<{ message: string }>(`/api/v1/admin/products/${props.productId}`, { method: 'DELETE', auth: 'admin', params: { motivo: motivo || undefined } })
    toast.sucesso(r.message)
    emit('alterado')
    emit('fechar')
  } catch (e) {
    toast.erro(e)
  } finally {
    enviando.value = false
  }
}

async function decidir(acao: 'aprovar' | 'rejeitar') {
  if (acao === 'rejeitar' && !rejeitando.value) { rejeitando.value = true; return }
  if (acao === 'rejeitar' && motivo.value.trim().length < 3) return toast.erro('Explique o motivo para o produtor.')
  enviando.value = true
  try {
    await api(`/api/v1/admin/products/${props.productId}/${acao}`, {
      method: 'POST', auth: 'admin', body: acao === 'rejeitar' ? { motivo: motivo.value } : undefined,
    })
    toast.sucesso(acao === 'aprovar' ? 'Produto aprovado e publicado na vitrine!' : 'Produto rejeitado. O produtor foi avisado.')
    emit('alterado')
    emit('fechar')
  } catch (e) {
    toast.erro(e)
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <Modal :aberto="productId !== null" titulo="Analisar Publicação" largura="max-w-3xl" @fechar="emit('fechar')">
    <div v-if="!produto" class="h-64 animate-pulse bg-slate-50 rounded-xl" />
    <div v-else class="grid sm:grid-cols-[14rem_1fr] gap-6">
      <div class="space-y-3">
        <div class="aspect-square rounded-2xl overflow-hidden border border-slate-100"><ImageBox :src="produto.imagens[fotoAtual]?.url" /></div>
        <div v-if="produto.imagens.length > 1" class="flex gap-2 flex-wrap">
          <button v-for="(img, i) in produto.imagens" :key="img.id" :class="['w-12 h-12 rounded-lg overflow-hidden border-2', i === fotoAtual ? 'border-nativo' : 'border-transparent']" @click="fotoAtual = Number(i)">
            <ImageBox :src="img.url" icon-class="w-4 h-4" />
          </button>
        </div>
        <div class="rounded-xl border border-slate-100 bg-slate-50 p-4">
          <p class="text-xs font-semibold uppercase text-slate-600">Produtor</p>
          <p class="font-medium text-slate-900 flex items-center gap-1.5 mt-1"><Icon name="user" class="w-4 h-4 text-nativo" /> {{ produto.produtor?.nome_loja }}</p>
          <p v-if="produto.produtor?.premium" class="text-xs text-destaque font-semibold mt-1 flex items-center gap-1"><Icon name="star" filled class="w-3 h-3" /> Premium</p>
        </div>
      </div>
      <div class="space-y-4">
        <div class="flex items-center gap-3 text-xs">
          <span class="badge bg-slate-100 text-slate-600">{{ produto.categoria }}</span>
          <span class="text-slate-600 flex items-center gap-1"><Icon name="map-pin" class="w-3.5 h-3.5" /> {{ produto.produtor?.local }}</span>
        </div>
        <div>
          <h3 class="text-2xl font-bold text-slate-900">{{ produto.nome }}</h3>
          <p class="text-sm text-slate-600">{{ moeda(produto.preco) }} · {{ produto.estoque }} un.{{ produto.lote ? ` · Lote ${produto.lote}` : '' }}</p>
        </div>
        <div>
          <p class="text-sm font-semibold text-slate-900 mb-1">Descrição Técnica</p>
          <p class="rounded-xl bg-slate-50 border border-slate-100 p-3 text-sm text-slate-600">{{ produto.descricao_tecnica || '—' }}</p>
        </div>
        <div>
          <p class="text-sm font-semibold text-terra mb-1">A história (Alma do Produto)</p>
          <p class="rounded-xl border border-terra-border bg-terra-light/50 p-3 text-sm italic text-terra">"{{ produto.historia || '—' }}"</p>
        </div>
        <div v-if="analise" :class="['rounded-xl border p-4 text-sm', corAnalise]">
          <p class="font-semibold flex items-center gap-2"><Icon name="shield-check" class="w-4 h-4" /> Verificação automática</p>
          <p class="mt-1 text-slate-700">{{ analise.resumo }}</p>
          <p class="mt-2 text-xs">Sugestão: <strong>{{ { aprovar: 'pode aprovar', revisar: 'revisar com atenção', rejeitar: 'provável rejeição' }[analise.recomendacao as string] }}</strong></p>
        </div>
        <div v-if="rejeitando">
          <label class="label">Motivo da rejeição (enviado ao produtor)</label>
          <textarea v-model="motivo" rows="3" class="input resize-none" placeholder="Ex: A descrição indica produto industrializado." />
        </div>
        <p v-if="produto.status !== 'pendente'" class="text-xs text-slate-600">
          Status atual: <strong>{{ produto.status }}</strong><span v-if="produto.motivo_rejeicao"> — {{ produto.motivo_rejeicao }}</span>
        </p>
      </div>
    </div>
    <template #rodape>
      <button class="btn-ghost text-red-600 border-red-200 mr-auto" :disabled="enviando || !produto" @click="excluir">
        <Icon name="trash" class="w-4 h-4" /> Excluir
      </button>
      <button class="btn-ghost" @click="emit('fechar')">Cancelar</button>
      <button class="btn bg-red-50 text-red-600 hover:bg-red-100 px-5 py-3" :disabled="enviando || !produto" @click="decidir('rejeitar')">
        <Icon name="x" class="w-4 h-4" /> {{ rejeitando ? 'Confirmar Rejeição' : 'Rejeitar' }}
      </button>
      <button class="btn-primary" :disabled="enviando || !produto || produto.status === 'aprovado'" @click="decidir('aprovar')">
        <Icon :name="enviando ? 'loader' : 'check'" class="w-4 h-4" /> Aprovar para Vitrine
      </button>
    </template>
  </Modal>
</template>
