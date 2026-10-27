<script setup lang="ts">
/** Meu perfil: dados da loja, história, endereço, privacidade e conta de recebimento (Mercado Pago). */
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, assetUrl } from '@/services/api'
import { toast } from '@/services/toast'
import { confirmar } from '@/services/confirm'
import { buscarCep, iniciais, mascaraCep, mascaraTelefone, telefone } from '@/utils/format'
import Icon from '@/components/ui/Icon.vue'
import Toggle from '@/components/ui/Toggle.vue'
import BottomNav from '@/components/ui/BottomNav.vue'
import { reduzirImagem } from '@/utils/imagem'
import { session } from '@/services/auth'

const route = useRoute()
const router = useRouter()

const perfil = reactive({
  id: 0, nome: '', nome_loja: '', email: '', cidade: '', estado: 'AC', cep: '', endereco: '', endereco_publico: false,
  telefone: '', whatsapp: '', descricao: '', foto_perfil: '', premium: false, premium_ate: null as string | null,
})
const mp = reactive({ conectado: false, conta: '', conectado_em: null as string | null, split_disponivel: false })
const modoPagamento = ref('simulado')
const previewFoto = ref('')
const arquivoFoto = ref<File | null>(null)
const fotoInput = ref<HTMLInputElement | null>(null)
const palavras = ref('')
const escrevendo = ref(false)
const salvando = ref(false)
const conectando = ref(false)

function preencher(data: any) {
  Object.assign(perfil, {
    ...data, whatsapp: telefone(data.whatsapp), cep: data.cep || '', endereco: data.endereco || '',
    email: data.email || '', telefone: data.telefone || '', descricao: data.descricao || '', cidade: data.cidade || '',
  })
  Object.assign(mp, data.mercadopago || {})
  modoPagamento.value = data.modo_pagamento
  previewFoto.value = data.foto_perfil ? assetUrl(data.foto_perfil) : ''
}

onMounted(async () => {
  const retorno = route.query.mp as string | undefined
  if (retorno) {
    const mensagens: Record<string, [string, boolean]> = {
      ok: ['Conta Mercado Pago conectada! As próximas vendas caem direto nela.', true],
      cancelado: ['Conexão com o Mercado Pago cancelada.', false],
      expirado: ['O link expirou. Tente conectar de novo.', false],
      erro: ['Não foi possível conectar ao Mercado Pago. Tente de novo.', false],
    }
    const [texto, ok] = mensagens[retorno] ?? mensagens.erro!
    ok ? toast.sucesso(texto) : toast.erro(texto)
    router.replace({ query: {} })
  }
  try { preencher(await api('/api/v1/producers/me', { auth: 'producer' })) } catch (e) { toast.erro(e) }
})

async function processarFoto(event: Event) {
  const original = (event.target as HTMLInputElement).files?.[0]
  if (!original) return
  if (!original.type.startsWith('image/')) return toast.erro('Escolha uma foto.')
  const arquivo = await reduzirImagem(original, 800) // foto de perfil pequena e leve
  if (!/^image\/(jpeg|png|webp|gif)$/.test(arquivo.type)) return toast.erro('Use uma foto JPG, PNG ou WEBP.')
  if (arquivo.size > 5 * 1024 * 1024) return toast.erro('A foto é grande demais. Tente outra.')
  arquivoFoto.value = arquivo
  previewFoto.value = URL.createObjectURL(arquivo)
}

async function onCep(valor: string) {
  perfil.cep = mascaraCep(valor)
  if (perfil.cep.length !== 9) return
  const r = await buscarCep(perfil.cep)
  if (r) {
    if (r.endereco) perfil.endereco = r.endereco
    perfil.cidade = r.cidade
    perfil.estado = r.uf
  }
}

async function sugerirTexto() {
  const base = palavras.value.trim() || perfil.descricao.trim()
  if (!base) return toast.erro('Escreva algumas palavras sobre a sua produção.')
  escrevendo.value = true
  try {
    const r = await api<{ texto: string }>('/api/v1/ai/generate', {
      method: 'POST', body: { prompt: base.slice(0, 500), tipo: 'produtor', nome: perfil.nome_loja || null },
    })
    perfil.descricao = r.texto
  } catch (e) {
    toast.erro(e)
  } finally {
    escrevendo.value = false
  }
}

async function salvarPerfil() {
  salvando.value = true
  try {
    const fd = new FormData()
    const campos: Record<string, string> = {
      nome: perfil.nome, nome_loja: perfil.nome_loja, email: perfil.email, cidade: perfil.cidade, estado: perfil.estado,
      cep: perfil.cep, endereco: perfil.endereco, endereco_publico: String(perfil.endereco_publico),
      telefone: perfil.telefone, whatsapp: perfil.whatsapp, descricao: perfil.descricao,
    }
    Object.entries(campos).forEach(([k, v]) => fd.append(k, v ?? ''))
    if (arquivoFoto.value) fd.append('foto_perfil', arquivoFoto.value)
    const r = await api('/api/v1/producers/me', { method: 'PUT', form: fd, auth: 'producer' })
    preencher(r.perfil)
    arquivoFoto.value = null
    toast.sucesso('Perfil salvo.')
  } catch (e) {
    toast.erro(e)
  } finally {
    salvando.value = false
  }
}

async function conectarMercadoPago() {
  conectando.value = true
  try {
    const { url } = await api<{ url: string }>('/api/v1/producers/me/mercadopago/conectar', { method: 'POST', auth: 'producer' })
    window.location.href = url   // o produtor faz login no próprio site do Mercado Pago
  } catch (e) {
    toast.erro(e)
    conectando.value = false
  }
}

const baixando = ref(false)
async function baixarMeusDados() {
  baixando.value = true
  try {
    const dados = await api('/api/v1/producers/me/dados', { auth: 'producer' })
    const blob = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `meus-dados-mercado-nativo-${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(link.href)
    toast.sucesso('Pronto! O arquivo com os seus dados foi baixado.')
  } catch (e) {
    toast.erro(e)
  } finally {
    baixando.value = false
  }
}

async function excluirMinhaConta() {
  const ok = await confirmar({
    titulo: 'Excluir a sua conta?',
    texto: 'Todos os seus produtos saem da vitrine e os seus dados pessoais (nome, WhatsApp, endereço, foto e história) são apagados. '
      + 'Os pedidos já pagos ficam no histórico, sem os seus dados. Isso não dá para desfazer.',
    sim: 'Sim, excluir minha conta', nao: 'Não, voltar', perigo: true,
  })
  if (!ok) return
  try {
    const r = await api<{ message: string }>('/api/v1/producers/me', { method: 'DELETE', auth: 'producer' })
    session.logoutProducer()
    toast.sucesso(r.message)
    router.push('/')
  } catch (e) {
    toast.erro(e)
  }
}

async function desconectarMercadoPago() {
  if (!(await confirmar({ titulo: 'Desconectar o Mercado Pago?', texto: 'As próximas vendas ficarão com a plataforma até você conectar de novo.', sim: 'Sim, desconectar', perigo: true }))) return
  try {
    const r = await api('/api/v1/producers/me/mercadopago', { method: 'DELETE', auth: 'producer' })
    preencher(r.perfil)
    toast.sucesso('Conta desconectada.')
  } catch (e) {
    toast.erro(e)
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 pt-5 sm:pt-10 px-4 pb-10">
    <div class="max-w-3xl mx-auto space-y-5 mb-nav">
      <div>
        <RouterLink to="/painel" class="back-link mb-3"><Icon name="arrow-left" class="w-4 h-4" /> Voltar ao painel</RouterLink>
        <h1 class="font-serif text-3xl font-bold text-slate-900">Meu perfil</h1>
        <p class="text-slate-600">É assim que os clientes conhecem você e a sua produção.</p>
      </div>

      <form class="card p-5 sm:p-8 space-y-6" @submit.prevent="salvarPerfil">
        <div class="flex flex-col sm:flex-row gap-6">
          <div class="flex flex-col items-center gap-2">
            <button type="button" class="relative w-28 h-28 rounded-full bg-nativo-dark text-white text-2xl font-bold overflow-hidden group shadow"
                    aria-label="Trocar foto" @click="fotoInput?.click()">
              <img v-if="previewFoto" :src="previewFoto" class="w-full h-full object-cover" alt="" />
              <span v-else>{{ iniciais(perfil.nome) }}</span>
              <span class="absolute inset-x-0 bottom-0 bg-black/55 text-xs font-medium py-1.5">Trocar foto</span>
            </button>
            <input ref="fotoInput" type="file" accept="image/*" class="hidden" @change="processarFoto" />
            <RouterLink v-if="perfil.id" :to="`/produtor/${perfil.id}`" class="text-xs text-nativo hover:underline flex items-center gap-1">
              <Icon name="external-link" class="w-3 h-3" /> Ver minha página
            </RouterLink>
          </div>
          <div class="flex-1 grid sm:grid-cols-2 gap-4">
            <div><label class="label" for="pf-nome">Seu nome</label><input id="pf-nome" v-model="perfil.nome" class="input" required autocomplete="name" /></div>
            <div><label class="label" for="pf-loja">Nome da propriedade ou ateliê</label><input id="pf-loja" v-model="perfil.nome_loja" class="input" required /></div>
            <div>
              <label class="label" for="pf-whats">WhatsApp (usado no login)</label>
              <input id="pf-whats" :value="perfil.whatsapp" class="input" inputmode="tel" autocomplete="tel"
                     @input="perfil.whatsapp = mascaraTelefone(($event.target as HTMLInputElement).value)" />
            </div>
            <div><label class="label" for="pf-email">E-mail (opcional)</label><input id="pf-email" v-model="perfil.email" type="email" class="input" autocomplete="email" /></div>
          </div>
        </div>

        <div>
          <label class="label" for="pf-historia">Sua história</label>
          <textarea id="pf-historia" v-model="perfil.descricao" rows="5" maxlength="3000" class="input resize-none"
                    placeholder="Como tudo começou, o que você produz, o que torna o seu trabalho especial..." />
          <div class="mt-2 flex flex-col sm:flex-row gap-2">
            <input v-model="palavras" class="input py-2.5" placeholder="Sem ideias? Digite palavras soltas: 3 gerações, sem agrotóxicos..." />
            <button type="button" class="btn-ai shrink-0 py-2.5" :disabled="escrevendo" @click="sugerirTexto">
              <Icon :name="escrevendo ? 'loader' : 'pen'" class="w-4 h-4" /> {{ escrevendo ? 'Escrevendo...' : 'Sugerir texto' }}
            </button>
          </div>
        </div>

        <div class="border-t border-slate-100 pt-6 space-y-4">
          <h2 class="font-serif text-lg font-bold text-slate-900">Onde retirar</h2>
          <div class="grid sm:grid-cols-3 gap-4">
            <div><label class="label" for="pf-cep">CEP</label><input id="pf-cep" :value="perfil.cep" class="input" inputmode="numeric" autocomplete="postal-code" @input="onCep(($event.target as HTMLInputElement).value)" /></div>
            <div class="sm:col-span-2"><label class="label" for="pf-end">Endereço</label><input id="pf-end" v-model="perfil.endereco" class="input" placeholder="Rua, número, bairro, ramal..." autocomplete="street-address" /></div>
            <div class="sm:col-span-2"><label class="label" for="pf-cidade">Cidade</label><input id="pf-cidade" v-model="perfil.cidade" class="input" /></div>
            <div><label class="label" for="pf-uf">Estado</label><select id="pf-uf" v-model="perfil.estado" class="input"><option>AC</option><option>AM</option><option>RO</option></select></div>
          </div>
          <div class="rounded-xl bg-slate-50 border border-slate-100 p-4 flex items-start justify-between gap-4">
            <div>
              <p class="font-medium text-slate-800">Mostrar o endereço completo na vitrine</p>
              <p class="text-xs text-slate-600 mt-0.5">Recomendamos deixar desligado: o cliente vê só a cidade e recebe o endereço pelo WhatsApp depois de pagar.</p>
            </div>
            <Toggle v-model="perfil.endereco_publico" />
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="btn-primary w-full sm:w-auto" :disabled="salvando"><Icon :name="salvando ? 'loader' : 'check'" class="w-4 h-4" /> Salvar perfil</button>
        </div>
      </form>

      <!-- Recebimentos -->
      <section class="card p-5 sm:p-8 space-y-4">
        <div class="flex items-start gap-3">
          <span class="w-11 h-11 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center shrink-0"><Icon name="wallet" class="w-5 h-5" /></span>
          <div>
            <h2 class="font-serif text-xl font-bold text-slate-900">Onde você recebe</h2>
            <p class="text-sm text-slate-600">Conecte sua conta Mercado Pago: a cada venda, 90% cai direto nela e 10% fica com a plataforma.
              Você entra no site do próprio Mercado Pago — <strong>não pedimos senha nem dados bancários</strong>.</p>
          </div>
        </div>

        <div v-if="mp.conectado" class="rounded-xl bg-nativo-soft border border-nativo-light p-4 flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-nativo flex items-center gap-2"><Icon name="shield-check" class="w-5 h-5" />
            <span>Conta conectada <span v-if="mp.conta" class="text-slate-600">(nº {{ mp.conta }})</span></span></p>
          <button class="text-sm text-slate-600 hover:text-red-600" @click="desconectarMercadoPago">Desconectar</button>
        </div>
        <template v-else>
          <button class="btn w-full sm:w-auto px-5 py-3 bg-[#009EE3] text-white hover:brightness-95" :disabled="conectando || !mp.split_disponivel" @click="conectarMercadoPago">
            <Icon :name="conectando ? 'loader' : 'link'" class="w-4 h-4" /> Conectar conta Mercado Pago
          </button>
          <p v-if="!mp.split_disponivel" class="text-xs text-slate-600">
            {{ modoPagamento === 'simulado'
              ? 'Os pagamentos estão em modo demonstração. A divisão automática aparece no extrato da plataforma.'
              : 'A conexão ainda não foi habilitada pela administração da plataforma. Enquanto isso, suas vendas são repassadas pela plataforma.' }}
          </p>
        </template>
      </section>

      <div class="card p-5 flex items-center justify-between gap-4">
        <div>
          <p class="text-xs text-slate-500 font-semibold">Plano</p>
          <p v-if="perfil.premium" class="font-semibold text-terra flex items-center gap-1.5"><Icon name="star" filled class="w-4 h-4" /> Premium
            <span v-if="perfil.premium_ate" class="text-xs text-slate-600 font-normal">até {{ new Date(perfil.premium_ate).toLocaleDateString('pt-BR') }}</span>
          </p>
          <p v-else class="font-semibold text-slate-700">Gratuito</p>
        </div>
        <RouterLink v-if="!perfil.premium" to="/painel?premium=1" class="btn-outline text-sm py-2.5">Conhecer o Premium</RouterLink>
      </div>

      <!-- LGPD: acesso, portabilidade e exclusão -->
      <section class="card p-5 sm:p-8 space-y-4" aria-labelledby="titulo-privacidade">
        <div class="flex items-start gap-3">
          <span class="w-11 h-11 rounded-xl bg-nativo-light text-nativo flex items-center justify-center shrink-0"><Icon name="lock" class="w-5 h-5" /></span>
          <div>
            <h2 id="titulo-privacidade" class="font-serif text-xl font-bold text-slate-900">Privacidade e seus dados</h2>
            <p class="text-slate-600">Veja como cuidamos dos seus dados na
              <RouterLink to="/politicas/privacidade" class="text-nativo font-semibold underline">Política de Privacidade</RouterLink>.</p>
          </div>
        </div>
        <div class="grid sm:grid-cols-2 gap-3">
          <button class="btn-outline" :disabled="baixando" @click="baixarMeusDados">
            <Icon :name="baixando ? 'loader' : 'download'" class="w-5 h-5" /> Baixar meus dados
          </button>
          <button class="btn border-2 border-red-200 text-red-700 bg-white hover:bg-red-50 px-5" @click="excluirMinhaConta">
            <Icon name="trash" class="w-5 h-5" /> Excluir minha conta
          </button>
        </div>
      </section>
    </div>
    <BottomNav variante="produtor" />
  </div>
</template>
