<script setup lang="ts">
/** "Mais Filtros": estado, cidade, raio de distância e localização do navegador. */
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/services/api'
import { toast } from '@/services/toast'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'

export interface FiltrosGeo { estado: string; cidade: string; raio: number; lat: number | null; lng: number | null; q: string }

const props = defineProps<{ aberto: boolean; filtros: FiltrosGeo; raioMaximo: number }>()
const emit = defineEmits<{ fechar: []; aplicar: [FiltrosGeo] }>()

const local = reactive<FiltrosGeo>({ ...props.filtros })

// Botões no lugar da barrinha deslizante (mais fácil para quem tem pouca firmeza na mão)
const DISTANCIAS = computed(() => [
  { valor: 5, texto: 'Até 5 km' },
  { valor: 20, texto: 'Até 20 km' },
  { valor: 50, texto: 'Até 50 km' },
  { valor: props.raioMaximo, texto: 'Qualquer distância' },
])
const raioEscolhido = computed(() => {
  const op = DISTANCIAS.value.find((o) => local.raio <= o.valor)
  return op ? op.valor : props.raioMaximo
})
const cidades = ref<string[]>([])
const localizando = ref(false)

async function carregarCidades() {
  try {
    cidades.value = await api<string[]>('/api/v1/public/cidades', { params: { uf: local.estado } })
  } catch {
    cidades.value = []
  }
}

watch(() => props.aberto, (v) => {
  if (v) {
    Object.assign(local, props.filtros)
    carregarCidades()
  }
})
watch(() => local.estado, () => { local.cidade = ''; carregarCidades() })

function usarMinhaLocalizacao() {
  if (!navigator.geolocation) return toast.erro('Seu navegador não permite localização.')
  localizando.value = true
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      local.lat = pos.coords.latitude
      local.lng = pos.coords.longitude
      local.cidade = ''
      if (local.raio >= props.raioMaximo) local.raio = 50
      localizando.value = false
      toast.sucesso('Localização encontrada!')
    },
    () => { localizando.value = false; toast.erro('Não foi possível obter sua localização. Escolha a cidade.') },
    { timeout: 10000 },
  )
}

function limpar() {
  Object.assign(local, { estado: 'AC', cidade: '', raio: props.raioMaximo, lat: null, lng: null, q: '' })
}
</script>

<template>
  <Modal :aberto="aberto" titulo="Escolher cidade e distância" icone="map-pin" @fechar="emit('fechar')">
    <div class="space-y-5">
      <div>
        <label class="label">Buscar</label>
        <input v-model="local.q" class="input-soft" placeholder="Ex.: geleia, alface, crochê..." />
      </div>
      <div class="grid grid-cols-3 gap-3">
        <div>
          <label class="label">Estado</label>
          <select v-model="local.estado" class="input-soft">
            <option value="AC">AC</option><option value="AM">AM</option><option value="RO">RO</option>
          </select>
        </div>
        <div class="col-span-2">
          <label class="label">Cidade</label>
          <select v-model="local.cidade" class="input-soft" @change="local.lat = null; local.lng = null">
            <option value="">Todo o estado</option>
            <option v-for="c in cidades" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>
      <button type="button" class="btn-outline w-full" :disabled="localizando" @click="usarMinhaLocalizacao">
        <Icon :name="localizando ? 'loader' : 'locate'" class="w-5 h-5" />
        {{ local.lat !== null ? 'Usando sua localização atual' : 'Usar minha localização atual' }}
      </button>
      <div>
        <p class="label">Até que distância?</p>
        <p v-if="!local.cidade && local.lat === null" class="text-sm text-slate-600 mb-2">Escolha uma cidade ou use sua localização para limitar a distância.</p>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2" role="radiogroup" aria-label="Distância máxima">
          <button v-for="op in DISTANCIAS" :key="op.valor" type="button" role="radio" :aria-checked="raioEscolhido === op.valor"
                  :disabled="op.valor < raioMaximo && !local.cidade && local.lat === null"
                  :class="['rounded-xl border-2 px-3 py-3 font-semibold text-base transition disabled:opacity-40',
                           raioEscolhido === op.valor ? 'border-nativo bg-nativo-light text-nativo' : 'border-slate-200 text-slate-700 hover:border-nativo']"
                  @click="local.raio = op.valor">
            {{ op.texto }}
          </button>
        </div>
      </div>
    </div>
    <template #rodape>
      <button class="btn-ghost mr-auto" @click="limpar">Limpar</button>
      <button class="btn-ghost" @click="emit('fechar')">Cancelar</button>
      <button class="btn-primary" @click="emit('aplicar', { ...local })"><Icon name="check" class="w-5 h-5" /> Mostrar produtos</button>
    </template>
  </Modal>
</template>
