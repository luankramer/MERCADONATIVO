<script setup lang="ts">
/** Cadastro e edição de produto, com sugestão de texto para "A Alma do Produto". */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'
import { CATEGORIAS, NOME_CATEGORIA } from '@/utils/categorias'
import { reduzirImagem } from '@/utils/imagem'
import { moeda } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const MAX_FOTOS = 6

const produto = reactive({ nome: '', preco: '' as string | number, lote: '', categoria: 'Alimentos', estoque: 0, descricao_tecnica: '', historia: '' })
const status = ref<{ status: string; motivo: string | null } | null>(null)
const fotosExistentes = ref<{ id: number; url: string }[]>([])
const removidas = ref<number[]>([])
const novasFotos = ref<{ arquivo: File; preview: string }[]>([])
const fotoInputRef = ref<HTMLInputElement | null>(null)
const cameraInputRef = ref<HTMLInputElement | null>(null)
const salvando = ref(false)

// "Quanto você recebe": venda - taxa do Mercado Pago - comissão do Mercado Nativo
const taxas = ref({ comissao: 10, pix: 0.99, credito: 4.98 })
api<{ percentual_plataforma: number; taxas_mercadopago?: { pix: number; credito: number } }>('/api/v1/checkout/config')
  .then((c) => { taxas.value = { comissao: c.percentual_plataforma, pix: c.taxas_mercadopago?.pix ?? 0.99, credito: c.taxas_mercadopago?.credito ?? 4.98 } })
  .catch(() => { /* mantém a estimativa padrão */ })
const precoNumero = computed(() => Number(String(produto.preco).replace(',', '.')) || 0)
function recebe(taxaMp: number) {
  const v = precoNumero.value
  const centavos = (x: number) => Math.round(x * 100) / 100
  return centavos(v - centavos(v * taxas.value.comissao / 100) - centavos(v * taxaMp / 100))
}
const carregandoEdicao = ref(false) // na edição: esqueleto até o produto chegar

// Galeria unificada: fotos já salvas + novas
const galeria = computed(() => [
  ...fotosExistentes.value.filter((f) => !removidas.value.includes(f.id)).map((f) => ({ chave: `e${f.id}`, url: f.url, id: f.id, nova: false })),
  ...novasFotos.value.map((f, i) => ({ chave: `n${i}`, url: f.preview, id: i, nova: true })),
])
const principal = computed(() => galeria.value[0]?.url)

onMounted(async () => {
  if (!isEdit.value) return
  carregandoEdicao.value = true
  try {
    const data = await api(`/api/v1/products/${route.params.id}`, { auth: 'producer' })
    Object.assign(produto, {
      nome: data.nome, preco: data.preco, lote: data.lote || '', categoria: data.categoria,
      estoque: data.estoque, descricao_tecnica: data.descricao_tecnica || '', historia: data.historia || '',
    })
    fotosExistentes.value = data.imagens
    status.value = { status: data.status, motivo: data.motivo_rejeicao }
  } catch (e) {
    toast.erro(e)
    router.replace('/painel')
  } finally {
    carregandoEdicao.value = false
  }
})
onBeforeUnmount(() => novasFotos.value.forEach((f) => URL.revokeObjectURL(f.preview)))

function abrirSeletorFoto() {
  fotoInputRef.value?.click()
}

async function processarFotos(event: Event) {
  const input = event.target as HTMLInputElement
  for (const original of Array.from(input.files ?? [])) {
    if (galeria.value.length >= MAX_FOTOS) { toast.erro(`Máximo de ${MAX_FOTOS} fotos por produto.`); break }
    if (!original.type.startsWith('image/')) { toast.erro(`"${original.name}" não é uma foto.`); continue }
    const arquivo = await reduzirImagem(original) // foto do celular fica leve para enviar
    if (arquivo.size > 5 * 1024 * 1024) { toast.erro(`"${original.name}" é grande demais. Tente outra foto.`); continue }
    novasFotos.value.push({ arquivo, preview: URL.createObjectURL(arquivo) })
  }
  input.value = ''
}

function removerFoto(item: { id: number; nova: boolean }) {
  if (item.nova) {
    const [f] = novasFotos.value.splice(item.id, 1)
    if (f) URL.revokeObjectURL(f.preview)
  } else removidas.value.push(item.id)
}

async function salvarProduto() {
  const preco = Number(String(produto.preco).replace(',', '.'))
  if (!produto.nome.trim()) return toast.erro('Informe o que você está vendendo.')
  if (!(preco > 0)) return toast.erro('Informe um preço válido.')
  salvando.value = true
  try {
    const formData = new FormData()
    formData.append('nome', produto.nome)
    formData.append('preco', String(preco))
    formData.append('categoria', produto.categoria)
    formData.append('estoque', String(Math.max(0, Math.floor(Number(produto.estoque) || 0))))
    formData.append('lote', produto.lote || '')
    formData.append('descricao_tecnica', produto.descricao_tecnica || '')
    formData.append('historia', produto.historia || '')
    if (isEdit.value) formData.append('remover_imagens', removidas.value.join(','))
    novasFotos.value.forEach((f) => formData.append('imagens', f.arquivo))

    const salvo = await api(isEdit.value ? `/api/v1/products/${route.params.id}` : '/api/v1/products', {
      method: isEdit.value ? 'PUT' : 'POST', form: formData, auth: 'producer',
    })
    toast.sucesso(salvo.status === 'pendente'
      ? 'Produto enviado! Ele aparece na vitrine assim que a equipe aprovar.'
      : 'Produto atualizado com sucesso!')
    router.push('/painel')
  } catch (e) {
    toast.erro(e)
  } finally {
    salvando.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 py-5 sm:py-10 px-4">
    <div class="max-w-5xl mx-auto card p-6 sm:p-8">
      <RouterLink to="/painel" class="back-link mb-5"><Icon name="arrow-left" class="w-4 h-4" /> Voltar ao Painel</RouterLink>
      <h1 class="font-serif text-3xl font-bold text-slate-900">{{ isEdit ? 'Editar Produto' : 'Novo Produto' }}</h1>
      <p class="text-slate-600 mt-1">{{ isEdit ? 'Atualize os detalhes do que a terra e suas mãos produziram com tanto carinho.' : 'Cadastre um novo produto' }}</p>

      <div v-if="carregandoEdicao" class="grid md:grid-cols-2 gap-8 mt-6" role="status" aria-live="polite">
        <span class="sr-only">Carregando o produto…</span>
        <div class="aspect-square rounded-2xl bg-slate-100 animate-pulse" aria-hidden="true" />
        <div class="space-y-4" aria-hidden="true"><div v-for="i in 5" :key="i" class="h-14 rounded-xl bg-slate-100 animate-pulse" /></div>
      </div>
      <template v-else>
      <div v-if="status?.status === 'pendente'" class="mt-5 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800 flex gap-2">
        <Icon name="clock" class="w-5 h-5 shrink-0" /> Este produto está em análise pela curadoria e ainda não aparece na vitrine.
      </div>
      <div v-else-if="status?.status === 'rejeitado'" class="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex gap-2">
        <Icon name="alert" class="w-5 h-5 shrink-0" /> <span>A curadoria pediu ajustes: <strong>{{ status.motivo }}</strong>. Corrija e salve para reenviar.</span>
      </div>
      <p class="mt-3 text-xs text-slate-500">Alterações no nome, categoria, descrição, história ou fotos passam por uma nova análise da curadoria. Preço, estoque e lote são atualizados na hora.</p>

      <div class="grid md:grid-cols-2 gap-8 mt-6">
        <div class="space-y-5">
          <input ref="fotoInputRef" type="file" accept="image/jpeg,image/png,image/webp" multiple class="hidden" @change="processarFotos" />
          <input ref="cameraInputRef" type="file" accept="image/*" capture="environment" class="hidden" @change="processarFotos" />
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button type="button" class="btn-primary" @click="cameraInputRef?.click()"><Icon name="camera" class="w-6 h-6 shrink-0" /> Tirar foto agora</button>
            <button type="button" class="btn-outline" @click="abrirSeletorFoto"><Icon name="image" class="w-6 h-6 shrink-0" /> Escolher da galeria</button>
          </div>
          <p class="text-sm text-slate-600 -mt-2">Dica: tire a foto de dia, perto de uma janela, com o produto sobre um pano liso.</p>
          <button type="button" class="relative w-full aspect-[16/9] rounded-2xl overflow-hidden bg-slate-300 group" @click="abrirSeletorFoto">
            <ImageBox v-if="principal" :src="principal" />
            <span :class="['absolute inset-0 flex flex-col items-center justify-center gap-2 text-white font-semibold text-sm transition',
                           principal ? 'bg-black/40 opacity-0 group-hover:opacity-100' : 'bg-slate-400/90']">
              <Icon name="camera" class="w-8 h-8" /> {{ principal ? 'Adicionar mais fotos' : 'Adicionar Foto Principal' }}
            </span>
          </button>
          <div class="flex flex-wrap gap-3">
            <div v-for="(item, i) in galeria" :key="item.chave" class="relative w-20 h-20 rounded-xl overflow-hidden border border-slate-200 group">
              <ImageBox :src="item.url" icon-class="w-5 h-5 text-slate-300" />
              <span v-if="i === 0" class="absolute bottom-0 inset-x-0 bg-nativo text-white text-xs font-bold text-center py-0.5">PRINCIPAL</span>
              <button type="button" class="absolute top-1 right-1 w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center shadow" title="Remover foto" @click="removerFoto(item)">
                <Icon name="x" class="w-3.5 h-3.5" />
              </button>
            </div>
            <button v-if="galeria.length < MAX_FOTOS" type="button" class="w-20 h-20 rounded-xl border-2 border-dashed border-nativo/40 text-nativo flex flex-col items-center justify-center text-xs font-semibold hover:bg-nativo-soft" @click="abrirSeletorFoto">
              <Icon name="plus" class="w-5 h-5" /> Mais Fotos
            </button>
          </div>

          <div>
            <label class="label">O que você está vendendo?</label>
            <input v-model="produto.nome" class="input" placeholder="Ex: Geleia de Cupuaçu" maxlength="255" />
          </div>
          <div class="grid grid-cols-5 gap-4">
            <div class="col-span-2">
              <label class="label">Preço (R$)</label>
              <input v-model="produto.preco" type="number" min="0.01" step="0.01" class="input" placeholder="28,00" aria-describedby="quanto-recebe" />
            </div>
            <div class="col-span-3">
              <label class="label">Lote / Safra (Opcional)</label>
              <input v-model="produto.lote" class="input" placeholder="Ex: Safra 2026" maxlength="100" />
            </div>
          </div>
          <div id="quanto-recebe" class="rounded-xl border border-nativo-light bg-nativo-soft p-4" aria-live="polite">
            <p class="font-semibold text-slate-900 flex items-center gap-2"><Icon name="wallet" class="w-5 h-5 text-nativo" /> Quanto você recebe por unidade</p>
            <template v-if="precoNumero > 0">
              <p class="mt-2 text-slate-800">No Pix: <strong class="text-nativo text-lg">{{ moeda(recebe(taxas.pix)) }}</strong></p>
              <p class="text-slate-800">No cartão: <strong class="text-nativo text-lg">{{ moeda(recebe(taxas.credito)) }}</strong></p>
              <p class="text-xs text-slate-600 mt-2">
                Valor estimado: {{ moeda(precoNumero) }} menos a taxa do Mercado Pago (cerca de {{ String(taxas.pix).replace('.', ',') }}% no Pix e até
                {{ String(taxas.credito).replace('.', ',') }}% no cartão) e a comissão de {{ taxas.comissao }}% do Mercado Nativo.
                <RouterLink to="/politicas/vendedores" target="_blank" class="underline">Entenda as taxas</RouterLink>
              </p>
            </template>
            <p v-else class="text-sm text-slate-600 mt-1">Digite o preço para ver quanto sobra para você depois das taxas.</p>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="label">Categoria</label>
              <select v-model="produto.categoria" class="input">
                <option v-for="c in CATEGORIAS" :key="c" :value="c">{{ NOME_CATEGORIA[c] }}</option>
              </select>
            </div>
            <div>
              <label class="label flex justify-between">Estoque <span class="text-xs text-slate-500 font-normal">Unidades</span></label>
              <input v-model.number="produto.estoque" type="number" min="0" step="1" class="input" />
            </div>
          </div>
          <div>
            <label class="label">Como é o produto? (tamanho, peso, ingredientes)</label>
            <textarea v-model="produto.descricao_tecnica" rows="3" class="input resize-none" placeholder="Ex: Sem conservantes, feito com adubação orgânica..." />
          </div>
        </div>

        <div class="rounded-2xl border border-terra-border bg-slate-50/80 p-5 flex flex-col">
          <h2 class="text-lg font-semibold text-terra flex items-center gap-2"><Icon name="pen" class="w-5 h-5" /> A história do produto</h2>
          <p class="text-slate-700 mt-1 mb-3">Conte a origem do produto: de onde vem, como é feito e o que ele tem de especial.</p>
          <textarea v-model="produto.historia" rows="12" class="input mt-1 flex-1 min-h-[16rem] font-serif italic text-slate-700 border-terra-border resize-none"
                    placeholder="Ex.: Colhemos o cupuaçu no quintal e cozinhamos em fogo baixo, como a vó ensinou..." />
        </div>
      </div>

      <div class="mt-8 pt-6 border-t border-slate-100 flex justify-end gap-3">
        <RouterLink to="/painel" class="btn-outline rounded-full px-6">Cancelar</RouterLink>
        <button class="btn-primary rounded-full px-6" :disabled="salvando" @click="salvarProduto">
          {{ salvando ? 'Salvando...' : isEdit ? 'Salvar Alterações' : 'Publicar Produto' }}
          <Icon :name="salvando ? 'loader' : 'check-circle'" class="w-5 h-5" />
        </button>
      </div>
      </template>
    </div>
  </div>
</template>
