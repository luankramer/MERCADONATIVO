import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Painel de depuração do Vue: ative com  set VUE_DEVTOOLS=1  (fica fora da tela nas apresentações)
    process.env.VUE_DEVTOOLS === '1' ? vueDevTools() : null,
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Libera o acesso pelo celular na mesma rede Wi-Fi (http://IP-DO-COMPUTADOR:5173)
    host: true,
    port: 5173,
  },
  preview: { host: true, port: 4173 },
  build: {
    // Compatível com iPhones a partir do iOS 14 e navegadores Android/desktop dos últimos anos
    target: ['es2020', 'safari14', 'chrome87', 'firefox78', 'edge88'],
  },
})
