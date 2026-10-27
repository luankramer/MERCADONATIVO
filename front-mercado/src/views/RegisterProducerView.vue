<script setup lang="ts">
/**
 * Cadastro do produtor em etapas: uma pergunta de cada vez, com exemplo e barra de progresso.
 * (Mais fácil para quem tem pouca experiência com formulários na internet.)
 */
import { computed, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import { buscarCep, mascaraCep, mascaraTelefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import FontSizeControl from '@/components/ui/FontSizeControl.vue'
import DicaVoz from '@/components/ui/DicaVoz.vue'

const router = useRouter()
const form = reactive({
  name: '', business_name: '', description: '', cep: '', address: '', city: 'Rio Branco', estado: 'AC', whatsapp: '',
})
const ETAPAS = ['Quem é você', 'Seu WhatsApp', 'Onde você fica', 'Sua história']
const aceite = ref(false)
const etapa = ref(1)
const palavrasIA = ref('')
const isLoading = ref(false)
const isGenerating = ref(false)
const buscandoCep = ref(false)
const titulo = ref<HTMLElement | null>(null)

const whatsappValido = computed(() => form.whatsapp.replace(/\D/g, '').length >= 10)

function erroDaEtapa(): string | null {
  if (etapa.value === 1) {
    if (form.name.trim().length < 2) return 'Escreva o seu nome.'
    if (form.business_name.trim().length < 2) return 'Escreva o nome do seu sítio, ateliê ou negócio.'
  }
  if (etapa.value === 2 && !whatsappValido.value) return 'Escreva o número do WhatsApp com DDD. Ex.: (68) 9 9999-9999'
  if (etapa.value === 3 && form.city.trim().length < 2) return 'Escreva a sua cidade.'
  if (etapa.value === 4 && !aceite.value) return 'Para terminar, marque que leu e aceita os Termos de Uso e a Política de Privacidade.'
  return null
}

async function irPara(n: number) {
  etapa.value = n
  await nextTick()
  window.scrollTo({ top: 0 })
  titulo.value?.focus()
}

function avancar() {
  const erro = erroDaEtapa()
  if (erro) return toast.erro(erro)
  if (etapa.value < ETAPAS.length) irPara(etapa.value + 1)
  else handleRegister()
}

async function handleAiAssist() {
  if (!palavrasIA.value.trim()) return toast.erro('Escreva algumas palavras sobre o seu trabalho.')
  isGenerating.value = true
  try {
    const data = await api<{ texto: string }>('/api/v1/ai/generate', {
      method: 'POST', body: { prompt: palavrasIA.value, tipo: 'produtor', nome: form.business_name || null },
    })
    form.description = data.texto
    toast.info('Texto sugerido. Leia e mude o que quiser.')
  } catch (e) {
    toast.erro(e)
  } finally {
    isGenerating.value = false
  }
}

async function onCep(valor: string) {
  form.cep = mascaraCep(valor)
  if (form.cep.length !== 9) return
  buscandoCep.value = true
  const r = await buscarCep(form.cep)
  buscandoCep.value = false
  if (r) {
    if (r.endereco) form.address = r.endereco
    form.city = r.cidade
    form.estado = r.uf
    toast.sucesso(`Achamos: ${r.cidade} - ${r.uf}`)
  }
}

async function handleRegister() {
  isLoading.value = true
  try {
    await api('/api/v1/auth/producer/register', { method: 'POST', body: { ...form, description: form.description || 'Produtor local.', aceite_termos: aceite.value } })
    toast.sucesso('Cadastro feito! Agora entre com o seu WhatsApp.')
    router.push('/login-produtor')
  } catch (e) {
    toast.erro(e)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-slate-50 py-6 sm:py-10 px-4 flex justify-center">
    <div class="w-full max-w-xl">
      <div class="flex items-center justify-between gap-3 mb-4">
        <button class="back-link" @click="etapa > 1 ? irPara(etapa - 1) : router.push('/login-produtor')">
          <Icon name="arrow-left" class="w-5 h-5" /> Voltar
        </button>
        <FontSizeControl />
      </div>

      <div class="card p-6 sm:p-8">
        <!-- Progresso -->
        <p class="text-base font-semibold text-slate-700">Etapa {{ etapa }} de {{ ETAPAS.length }}</p>
        <div class="grid grid-cols-4 gap-2 mt-2 mb-6" aria-hidden="true">
          <span v-for="n in ETAPAS.length" :key="n" :class="['h-2.5 rounded-full', n <= etapa ? 'bg-nativo' : 'bg-slate-200']" />
        </div>

        <form @submit.prevent="avancar">
          <!-- 1: quem é você -->
          <section v-if="etapa === 1" class="space-y-5">
            <h1 ref="titulo" tabindex="-1" class="font-serif text-3xl font-bold text-slate-900 outline-none">Vamos começar! Quem é você?</h1>
            <div>
              <label class="label" for="rp-nome">Seu nome</label>
              <input id="rp-nome" v-model="form.name" autocomplete="name" class="input" placeholder="Ex.: Maria da Silva" />
            </div>
            <div>
              <label class="label" for="rp-negocio">Nome do seu sítio, ateliê ou negócio</label>
              <input id="rp-negocio" v-model="form.business_name" class="input" placeholder="Ex.: Sítio São José" />
              <p class="text-sm text-slate-600 mt-1.5">É o nome que os compradores vão ver na vitrine.</p>
            </div>
          </section>

          <!-- 2: WhatsApp -->
          <section v-else-if="etapa === 2" class="space-y-5">
            <h1 ref="titulo" tabindex="-1" class="font-serif text-3xl font-bold text-slate-900 outline-none">Qual é o seu WhatsApp?</h1>
            <div class="rounded-xl bg-nativo-soft border border-nativo-light p-4 text-slate-700 flex gap-3">
              <Icon name="lock" class="w-6 h-6 text-nativo shrink-0" />
              <p>Você <strong>não precisa de senha</strong>. Para entrar, a gente manda um código para este número.</p>
            </div>
            <div>
              <label class="label" for="rp-whats">Número com DDD</label>
              <input id="rp-whats" :value="form.whatsapp" class="input text-xl tracking-wide" placeholder="(68) 9 9999-9999" inputmode="tel" autocomplete="tel"
                     @input="form.whatsapp = mascaraTelefone(($event.target as HTMLInputElement).value)" />
            </div>
          </section>

          <!-- 3: localização -->
          <section v-else-if="etapa === 3" class="space-y-5">
            <h1 ref="titulo" tabindex="-1" class="font-serif text-3xl font-bold text-slate-900 outline-none">Onde você fica?</h1>
            <p class="text-slate-600">Assim os compradores da sua região encontram você. O endereço completo só aparece se você quiser.</p>
            <div>
              <label class="label flex items-center gap-2" for="rp-cep">CEP (se souber) <Icon v-if="buscandoCep" name="loader" class="w-4 h-4 text-nativo" /></label>
              <input id="rp-cep" :value="form.cep" class="input" placeholder="00000-000" inputmode="numeric" autocomplete="postal-code"
                     @input="onCep(($event.target as HTMLInputElement).value)" />
              <p class="text-sm text-slate-600 mt-1.5">Com o CEP a cidade é preenchida sozinha.</p>
            </div>
            <div class="grid grid-cols-[1fr_auto] gap-3">
              <div>
                <label class="label" for="rp-cidade">Cidade</label>
                <input id="rp-cidade" v-model="form.city" class="input" placeholder="Ex.: Rio Branco" />
              </div>
              <div>
                <label class="label" for="rp-uf">Estado</label>
                <select id="rp-uf" v-model="form.estado" class="input w-24"><option>AC</option><option>AM</option><option>RO</option></select>
              </div>
            </div>
            <div>
              <label class="label" for="rp-end">Endereço ou comunidade (opcional)</label>
              <input id="rp-end" v-model="form.address" class="input" placeholder="Ex.: Ramal do Bujari, km 8" />
            </div>
          </section>

          <!-- 4: história -->
          <section v-else class="space-y-5">
            <h1 ref="titulo" tabindex="-1" class="font-serif text-3xl font-bold text-slate-900 outline-none">Conte um pouco da sua história</h1>
            <p class="text-slate-600">Isto é opcional, mas ajuda muito a vender. Pode ser simples: há quanto tempo você trabalha, o que produz, como aprendeu.</p>
            <DicaVoz />
            <div>
              <label class="label" for="rp-hist">Sua história</label>
              <textarea id="rp-hist" v-model="form.description" rows="6" class="input resize-none" placeholder="Ex.: Planto com a minha família há 20 anos, sem veneno..." />
            </div>
            <details class="rounded-2xl border border-terra-border bg-terra-light p-4">
              <summary class="cursor-pointer font-semibold text-terra min-h-[32px]">Não sabe o que escrever? A gente ajuda</summary>
              <p class="text-slate-700 mt-2">Escreva algumas palavras e toque em "Sugerir texto". Depois é só ajustar do seu jeito.</p>
              <input v-model="palavrasIA" class="input mt-3 border-terra-border" placeholder="Ex.: 20 anos, orgânico, família" @keydown.enter.prevent="handleAiAssist" />
              <button type="button" class="btn-ai w-full mt-3" :disabled="isGenerating" @click="handleAiAssist">
                <Icon :name="isGenerating ? 'loader' : 'pen'" class="w-5 h-5" /> {{ isGenerating ? 'Escrevendo...' : 'Sugerir texto' }}
              </button>
            </details>
          </section>

          <label v-if="etapa === ETAPAS.length" class="mt-8 flex items-start gap-3 rounded-2xl border-2 border-slate-200 p-4 cursor-pointer has-[:checked]:border-nativo has-[:checked]:bg-nativo-soft">
            <input v-model="aceite" type="checkbox" class="mt-1 w-6 h-6 shrink-0 accent-nativo" />
            <span class="text-slate-800">
              Li e aceito os <RouterLink to="/politicas/termos" target="_blank" class="text-nativo font-semibold underline">Termos de Uso</RouterLink>,
              as <RouterLink to="/politicas/vendedores" target="_blank" class="text-nativo font-semibold underline">Regras para Vendedores</RouterLink>
              e a <RouterLink to="/politicas/privacidade" target="_blank" class="text-nativo font-semibold underline">Política de Privacidade</RouterLink>.
              <span class="block text-sm text-slate-600 mt-1">Os links abrem em outra aba, sem perder o que você já preencheu.</span>
            </span>
          </label>

          <button type="submit" :disabled="isLoading" class="btn-primary w-full py-4 text-lg mt-6">
            <template v-if="etapa < ETAPAS.length">Continuar <Icon name="arrow-right" class="w-5 h-5" /></template>
            <template v-else><Icon :name="isLoading ? 'loader' : 'check-circle'" class="w-5 h-5" /> {{ isLoading ? 'Salvando...' : 'Terminar cadastro' }}</template>
          </button>
          <p v-if="etapa === ETAPAS.length" class="text-center text-sm text-slate-600 mt-3">Você pode mudar tudo isso depois em "Meu perfil".</p>
        </form>
      </div>

      <p class="text-center mt-6 text-slate-600">
        Já tem cadastro? <RouterLink to="/login-produtor" class="font-semibold text-nativo underline">Entrar</RouterLink>
      </p>
    </div>
  </main>
</template>
