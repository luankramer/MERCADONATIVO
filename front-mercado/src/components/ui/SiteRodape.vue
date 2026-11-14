<script setup lang="ts">
/** Rodapé das páginas públicas: SAC (WhatsApp, telefone e e-mail da equipe), ajuda e políticas. */
import { computed } from 'vue'
import Icon from '@/components/ui/Icon.vue'
import {
  SAC_EMAIL, linkEmailSac, linkTelefoneSac, linkWhatsappSac, telefoneSacFormatado, temSac, whatsappSacFormatado,
} from '@/utils/suporte'

// empilhado: botões um embaixo do outro (para páginas de coluna estreita, como a do pedido)
const props = defineProps<{ mensagem?: string; empilhado?: boolean }>()
const whatsapp = computed(() => linkWhatsappSac(props.mensagem))
const email = linkEmailSac()
</script>

<template>
  <footer class="mt-10 border-t border-slate-200 pt-8 space-y-8" aria-label="Rodapé">
    <section v-if="temSac" id="sac" aria-labelledby="titulo-sac" class="rounded-2xl bg-white border border-slate-200 p-5 sm:p-6 scroll-mt-4">
      <h2 id="titulo-sac" class="font-serif text-xl font-bold text-slate-900 flex items-center gap-2">
        <Icon name="help" class="w-6 h-6 text-nativo" /> SAC: fale com a equipe do Mercado Nativo
      </h2>
      <p class="text-slate-600 mt-1">Dúvidas, problemas com um pedido ou pedido de devolução. Atendemos pelo canal que for mais fácil para você.</p>
      <div :class="['mt-4 grid gap-3', empilhado ? '' : 'md:grid-cols-3']">
        <a v-if="whatsapp" :href="whatsapp" target="_blank" rel="noopener"
           class="btn-primary justify-start text-left py-3 px-4 min-h-[56px] min-w-0">
          <Icon name="message" class="w-6 h-6 shrink-0" />
          <span><span class="block font-bold">WhatsApp</span><span class="block text-sm text-white/90">{{ whatsappSacFormatado }}</span></span>
        </a>
        <a v-if="linkTelefoneSac" :href="linkTelefoneSac"
           class="btn-outline justify-start text-left py-3 px-4 min-h-[56px] min-w-0">
          <Icon name="phone" class="w-6 h-6 shrink-0" />
          <span><span class="block font-bold">Telefone</span><span class="block text-sm">{{ telefoneSacFormatado }}</span></span>
        </a>
        <a v-if="email" :href="email"
           class="btn-outline justify-start text-left py-3 px-4 min-h-[56px] min-w-0">
          <Icon name="mail" class="w-6 h-6 shrink-0" />
          <span class="min-w-0"><span class="block font-bold">E-mail</span><span class="block text-sm [overflow-wrap:anywhere]">{{ SAC_EMAIL }}</span></span>
        </a>
      </div>
    </section>

    <nav aria-label="Políticas" class="flex flex-wrap gap-x-6 gap-y-2 text-base">
      <RouterLink to="/politicas/privacidade" class="text-slate-700 underline underline-offset-4 py-1">Privacidade</RouterLink>
      <RouterLink to="/politicas/termos" class="text-slate-700 underline underline-offset-4 py-1">Termos de Uso</RouterLink>
      <RouterLink to="/politicas/compras" class="text-slate-700 underline underline-offset-4 py-1">Compras e cancelamentos</RouterLink>
      <RouterLink to="/politicas/vendedores" class="text-slate-700 underline underline-offset-4 py-1">Regras para vendedores</RouterLink>
      <RouterLink to="/politicas/cookies" class="text-slate-700 underline underline-offset-4 py-1">Cookies</RouterLink>
    </nav>

    <div class="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600 pb-2">
      <span class="flex items-center gap-1.5"><img src="/logo-simbolo.svg" alt="" class="w-5 h-auto" width="20" height="18" /> Mercado Nativo · "Onde a cultura encontra o consumo consciente."</span>
      <RouterLink to="/ajuda" class="flex items-center gap-1.5 p-2 font-semibold text-nativo hover:underline">
        <Icon name="help" class="w-5 h-5" /> Ajuda: como comprar e vender
      </RouterLink>
      <RouterLink to="/admin/login" class="flex items-center gap-1.5 p-2 hover:text-slate-800">
        <Icon name="shield" class="w-4 h-4" /> Acesso restrito
      </RouterLink>
    </div>
  </footer>
</template>
