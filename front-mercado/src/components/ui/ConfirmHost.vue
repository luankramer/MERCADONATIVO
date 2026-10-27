<script setup lang="ts">
/** Mostra a janela pedida por confirmar() (services/confirm.ts). Fica montada uma vez no App.vue. */
import { confirmacao } from '@/services/confirm'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
</script>

<template>
  <Modal :aberto="confirmacao.aberta" largura="max-w-md" @fechar="confirmacao.responder(false)">
    <div v-if="confirmacao.pedido" class="text-center py-2">
      <span :class="['w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4',
                     confirmacao.pedido.perigo ? 'bg-red-50 text-red-600' : 'bg-nativo-light text-nativo']">
        <Icon :name="confirmacao.pedido.perigo ? 'alert' : 'check-circle'" class="w-8 h-8" />
      </span>
      <h2 class="font-serif text-2xl font-bold text-slate-900">{{ confirmacao.pedido.titulo }}</h2>
      <p v-if="confirmacao.pedido.texto" class="mt-2 text-slate-600">{{ confirmacao.pedido.texto }}</p>
      <div v-if="confirmacao.pedido.motivo" class="mt-4 text-left">
        <label class="label" for="confirm-motivo">{{ confirmacao.pedido.motivo.rotulo }}</label>
        <textarea id="confirm-motivo" v-model="confirmacao.texto" rows="3" maxlength="300" class="input resize-none"
                  :placeholder="confirmacao.pedido.motivo.placeholder" />
      </div>
      <div class="mt-6 flex flex-col gap-3">
        <button :class="['btn w-full py-3.5 text-lg text-white', confirmacao.pedido.perigo ? 'bg-red-600 hover:bg-red-700' : 'bg-nativo hover:bg-nativo-dark']"
                @click="confirmacao.responder(true)">
          {{ confirmacao.pedido.sim || 'Sim, continuar' }}
        </button>
        <button class="btn-ghost w-full py-3.5 text-lg" @click="confirmacao.responder(false)">
          {{ confirmacao.pedido.nao || 'Não, voltar' }}
        </button>
      </div>
    </div>
  </Modal>
</template>
