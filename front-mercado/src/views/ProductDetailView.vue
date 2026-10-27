<script setup lang="ts">
/** Página do produto: galeria, história, produtor, compra (PIX / WhatsApp) e avaliações. */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, assetUrl } from '@/services/api'
import { prefs } from '@/services/preferences'
import { toast } from '@/services/toast'
import { iniciais, moeda } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import ImageBox from '@/components/ui/ImageBox.vue'
import StarRating from '@/components/ui/StarRating.vue'
import CheckoutModal from '@/components/catalog/CheckoutModal.vue'
import PublicHeader from '@/components/catalog/PublicHeader.vue'
import { falando, falar, pararFala, vozDisponivel } from '@/services/voz'

interface Avaliacao { id: number; nome: string; nota: number; comentario: string | null }

const route = useRoute()
const router = useRouter()
const produto = ref<any>(null)
const avaliacoes = ref<Avaliacao[]>([])
const fotoAtual = ref(0)
const carregando = ref(true)
const checkoutAberto = ref(false)
const abrindoWhats = ref(false)
const novaAvaliacao = reactive({ nome: '', nota: 5, comentario: '' })
const enviandoAvaliacao = ref(false)

const esgotado = computed(() => (produto.value?.estoque ?? 0) <= 0)
const fotos = computed<{ id: number; url: string }[]>(() => produto.value?.imagens ?? [])
const seguindo = computed(() => produto.value && prefs.isSeguindo(produto.value.produtor.id))

async function carregar() {
  carregando.value = true
  try {
    const id = route.params.id
    produto.value = await api(`/api/v1/public/products/${id}`)
    avaliacoes.value = await api(`/api/v1/public/products/${id}/reviews`)
    fotoAtual.value = 0
  } catch (e: any) {
    toast.erro(e)
    if (e.status === 404) router.replace('/')
  } finally {
    carregando.value = false
  }
}

async function reservarWhatsApp() {
  abrindoWhats.value = true
  try {
    const { link } = await api<{ link: string }>(`/api/v1/public/products/${produto.value.id}/contato`, { method: 'POST' })
    window.open(link, '_blank', 'noopener')
  } catch (e) {
    toast.erro(e)
  } finally {
    abrindoWhats.value = false
  }
}

async function seguir() {
  const id = produto.value.produtor.id
  const agora = prefs.alternarSeguir(id)
  try {
    await api(`/api/v1/public/producers/${id}/seguir`, { method: 'POST', params: { seguir: agora } })
    toast.sucesso(agora ? `Você está seguindo ${produto.value.produtor.nome_loja}!` : 'Você deixou de seguir.')
  } catch { /* contador é apenas informativo */ }
}

async function enviarAvaliacao() {
  if (!novaAvaliacao.nome.trim()) return toast.erro('Informe seu nome.')
  enviandoAvaliacao.value = true
  try {
    await api(`/api/v1/public/products/${produto.value.id}/reviews`, { method: 'POST', body: novaAvaliacao })
    toast.sucesso('Obrigado pela sua avaliação!')
    Object.assign(novaAvaliacao, { nome: '', nota: 5, comentario: '' })
    avaliacoes.value = await api(`/api/v1/public/products/${produto.value.id}/reviews`)
    const atual = await api(`/api/v1/public/products/${produto.value.id}`, { params: { registrar_visita: false } })
    produto.value.nota_media = atual.nota_media
    produto.value.total_avaliacoes = atual.total_avaliacoes
  } catch (e) {
    toast.erro(e)
  } finally {
    enviandoAvaliacao.value = false
  }
}

function ouvir() {
  if (falando.value) return pararFala()
  const p = produto.value
  const partes = [
    `${p.nome}. Preço: ${moeda(p.preco).replace('R$', '')} reais.`,
    esgotado.value ? 'Produto esgotado no momento.' : `Tem ${p.estoque} disponíveis.`,
    p.descricao_tecnica ? `Sobre o produto: ${p.descricao_tecnica}` : '',
    p.historia ? `A história: ${p.historia}` : '',
    `Feito por ${p.produtor.nome_loja}, em ${p.produtor.local}. A retirada é combinada pelo WhatsApp.`,
  ]
  falar(partes.filter(Boolean).join(' '))
}

watch(() => route.params.id, (id) => { pararFala(); if (id) carregar() })
onBeforeUnmount(pararFala)
onMounted(carregar)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <PublicHeader />
    <main class="max-w-5xl mx-auto px-4 pt-3 sm:pt-6 pb-36 md:pb-12">
      <RouterLink to="/" class="back-link mb-4"><Icon name="arrow-left" class="w-5 h-5" /> Voltar para os produtos</RouterLink>

      <div v-if="carregando" class="grid md:grid-cols-2 gap-8">
        <div class="aspect-square rounded-3xl bg-white animate-pulse" />
        <div class="space-y-4"><div class="h-10 bg-white rounded-xl animate-pulse" /><div class="h-40 bg-white rounded-xl animate-pulse" /></div>
      </div>

      <template v-else-if="produto">
        <div class="grid md:grid-cols-2 gap-8">
          <!-- Galeria -->
          <div>
            <div class="relative aspect-square rounded-3xl overflow-hidden bg-white border border-slate-100 shadow-sm">
              <ImageBox :src="fotos[fotoAtual]?.url" :alt="produto.nome" icon-class="w-20 h-20 text-slate-300" />
              <button class="absolute top-3 right-3 h-12 px-4 rounded-full bg-white shadow-md flex items-center gap-2 font-semibold text-slate-800"
                      :aria-pressed="prefs.isFavorito(produto.id)"
                      @click="prefs.alternarFavorito(produto.id)">
                <Icon name="heart" :filled="prefs.isFavorito(produto.id)" :class="['w-6 h-6', prefs.isFavorito(produto.id) ? 'text-red-500' : 'text-slate-600']" />
                {{ prefs.isFavorito(produto.id) ? 'Guardado' : 'Guardar' }}
              </button>
              <div v-if="esgotado" class="absolute bottom-0 inset-x-0 bg-slate-800/90 text-white font-semibold py-2.5 text-center">Esgotado no momento</div>
            </div>
            <div v-if="fotos.length > 1" class="flex gap-3 mt-4 overflow-x-auto">
              <button v-for="(f, i) in fotos" :key="f.id"
                      :class="['w-20 h-20 shrink-0 rounded-xl overflow-hidden border-2', i === fotoAtual ? 'border-nativo' : 'border-transparent opacity-70']"
                      @click="fotoAtual = i">
                <ImageBox :src="f.url" icon-class="w-6 h-6 text-slate-300" />
              </button>
            </div>
          </div>

          <!-- Informações -->
          <div class="space-y-5">
            <div class="flex items-center justify-between">
              <span class="badge bg-nativo-light text-nativo">{{ produto.categoria }}</span>
              <span v-if="produto.nota_media" class="flex items-center gap-1 text-sm font-semibold text-terra-dark bg-terra-light px-2.5 py-1 rounded-lg">
                <Icon name="star" filled class="w-4 h-4" /> {{ produto.nota_media.toFixed(1) }}
                <span class="text-slate-500 font-normal text-xs">({{ produto.total_avaliacoes }} avaliações)</span>
              </span>
            </div>
            <div>
              <h1 class="font-serif text-3xl sm:text-4xl font-bold text-slate-900 leading-tight">{{ produto.nome }}</h1>
              <p class="text-4xl font-bold text-nativo mt-2">{{ moeda(produto.preco) }}</p>
              <button v-if="vozDisponivel" type="button" class="btn-ghost mt-3" :aria-pressed="falando" @click="ouvir">
                <Icon :name="falando ? 'x' : 'volume'" class="w-5 h-5" /> {{ falando ? 'Parar de ouvir' : 'Ouvir a descrição' }}
              </button>
              <p v-if="produto.lote" class="text-xs text-slate-600 mt-1">Lote / Safra: {{ produto.lote }}</p>
            </div>

            <div v-if="esgotado" class="rounded-xl border border-slate-200 bg-slate-100 px-4 py-3 text-sm font-medium text-slate-600 flex items-center gap-2">
              <Icon name="package" class="w-5 h-5" /> Produto esgotado no momento. Siga o produtor para saber da próxima safra.
            </div>
            <div v-else-if="produto.estoque <= 15" class="rounded-xl border border-terra-border bg-terra-light px-4 py-3 text-sm font-medium text-terra-dark flex items-center gap-2">
              <Icon name="clock" class="w-5 h-5 shrink-0" /> Restam {{ produto.estoque }} unidades deste lote.
            </div>

            <div v-if="produto.descricao_tecnica" class="card p-5">
              <h2 class="text-lg font-semibold text-slate-900 flex items-center gap-2 mb-2"><Icon name="shopping-bag" class="w-5 h-5" /> Sobre o produto</h2>
              <p class="text-slate-700 leading-relaxed whitespace-pre-line">{{ produto.descricao_tecnica }}</p>
            </div>

            <div v-if="produto.historia" class="rounded-2xl border border-terra-border bg-terra-light/60 p-5">
              <h2 class="text-lg font-semibold text-terra mb-2">A história deste produto</h2>
              <p class="font-serif text-lg text-terra-dark leading-relaxed">"{{ produto.historia }}"</p>
            </div>

            <!-- Produtor -->
            <div class="card p-4 flex items-center gap-4">
              <RouterLink :to="`/produtor/${produto.produtor.id}`" class="w-14 h-14 shrink-0 rounded-full bg-nativo-dark text-white flex items-center justify-center font-bold overflow-hidden">
                <img v-if="produto.produtor.foto_perfil" :src="assetUrl(produto.produtor.foto_perfil)" class="w-full h-full object-cover" alt="" />
                <span v-else>{{ iniciais(produto.produtor.nome_loja) }}</span>
              </RouterLink>
              <div class="flex-1 min-w-0">
                <RouterLink :to="`/produtor/${produto.produtor.id}`" class="font-semibold text-slate-900 hover:underline">{{ produto.produtor.nome_loja }}</RouterLink>
                <p class="text-xs text-slate-600">Por {{ produto.produtor.nome }}</p>
                <p class="text-xs text-slate-500 flex items-center gap-1 truncate">
                  <Icon name="map-pin" class="w-3 h-3 shrink-0" />
                  {{ produto.produtor.endereco ? `${produto.produtor.endereco} - ` : '' }}{{ produto.produtor.local }}
                </p>
                <p class="text-sm text-terra flex items-center gap-1"><Icon name="clock" class="w-4 h-4" /> Combine o horário pelo WhatsApp</p>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 -mt-2">
              <RouterLink :to="`/produtor/${produto.produtor.id}`" class="btn-ghost flex-1"><Icon name="user" class="w-5 h-5" /> Ver o produtor</RouterLink>
              <button :class="['btn flex-1 px-4', seguindo ? 'bg-white border-2 border-nativo text-nativo' : 'bg-nativo-light text-nativo border-2 border-nativo-light']" :aria-pressed="seguindo" @click="seguir">
                <Icon name="bell" class="w-5 h-5" /> {{ seguindo ? 'Seguindo ✓' : 'Seguir produtor' }}
              </button>
            </div>

            <div class="hidden md:grid gap-3">
              <button class="btn-primary py-4 text-lg" :disabled="esgotado" @click="checkoutAberto = true">
                <Icon name="shopping-bag" class="w-6 h-6" /> Comprar agora
              </button>
              <button class="btn-outline py-3.5" :disabled="abrindoWhats" @click="reservarWhatsApp">
                <Icon :name="abrindoWhats ? 'loader' : 'phone'" class="w-5 h-5" /> Falar com o produtor no WhatsApp
              </button>
              <p class="text-sm text-slate-600 text-center flex items-center justify-center gap-1.5"><Icon name="credit-card" class="w-4 h-4" /> Crédito, débito ou Pix · retirada no local</p>
            </div>
          </div>
        </div>

        <!-- Avaliações -->
        <section class="mt-12 pt-10 border-t border-slate-200">
          <h2 class="font-serif text-2xl font-bold text-slate-900 flex items-center gap-2 mb-6">
            <Icon name="message" class="w-6 h-6 text-nativo" /> O que dizem nossos clientes
          </h2>
          <div v-if="avaliacoes.length" class="grid md:grid-cols-2 gap-4">
            <div v-for="a in avaliacoes" :key="a.id" class="card p-5">
              <StarRating :valor="a.nota" />
              <p v-if="a.comentario" class="italic text-slate-600 mt-3 leading-relaxed">"{{ a.comentario }}"</p>
              <div class="flex items-center gap-3 mt-4">
                <span class="w-9 h-9 rounded-full bg-slate-200 text-slate-600 font-semibold flex items-center justify-center">{{ iniciais(a.nome).slice(0, 1) }}</span>
                <span class="font-semibold text-slate-900 text-sm">{{ a.nome }}</span>
              </div>
            </div>
          </div>
          <p v-else class="text-slate-600">Ainda não há avaliações. Seja o primeiro a avaliar!</p>

          <form class="mt-10 max-w-2xl space-y-4" @submit.prevent="enviarAvaliacao">
            <h3 class="font-serif text-2xl font-bold text-slate-900">Deixe sua avaliação</h3>
            <div class="grid sm:grid-cols-2 gap-4 items-end">
              <div>
                <label class="label">Seu nome</label>
                <input v-model="novaAvaliacao.nome" class="input" placeholder="Ex: João da Silva" required minlength="2" maxlength="120" />
              </div>
              <StarRating v-model="novaAvaliacao.nota" editavel tamanho="w-8 h-8" class="pb-1" />
            </div>
            <textarea v-model="novaAvaliacao.comentario" rows="4" class="input resize-none" placeholder="Deixe seu comentário" maxlength="1000" />
            <button type="submit" class="btn-primary w-full py-4" :disabled="enviandoAvaliacao">
              Enviar avaliação <Icon :name="enviandoAvaliacao ? 'loader' : 'check-circle'" class="w-5 h-5" />
            </button>
          </form>
        </section>

        <CheckoutModal :aberto="checkoutAberto" :produto="produto" @fechar="checkoutAberto = false" />

        <!-- Barra de compra fixa no celular -->
        <div class="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur border-t border-slate-200 px-4 pt-3 pb-safe">
          <div class="flex items-center justify-between pb-2">
            <p class="text-sm text-slate-600">{{ esgotado ? 'Esgotado no momento' : 'Crédito, débito ou Pix' }}</p>
            <p class="text-2xl font-bold text-nativo tabular-nums">{{ moeda(produto.preco) }}</p>
          </div>
          <div class="grid grid-cols-2 gap-2 pb-3">
            <button class="btn border-2 border-nativo text-nativo bg-white px-2" :disabled="abrindoWhats" @click="reservarWhatsApp">
              <Icon :name="abrindoWhats ? 'loader' : 'phone'" class="w-5 h-5" /> Conversar
            </button>
            <button class="btn-primary px-2 text-lg" :disabled="esgotado" @click="checkoutAberto = true"><Icon name="shopping-bag" class="w-5 h-5" /> Comprar</button>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
