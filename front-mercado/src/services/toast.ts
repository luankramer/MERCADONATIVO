/** Avisos rápidos (substituem os alert() do navegador). */
import { reactive } from 'vue'

export interface Toast { id: number; tipo: 'sucesso' | 'erro' | 'info'; texto: string }

export const toasts = reactive<Toast[]>([])
let seq = 0

// Avisos ficam mais tempo na tela (público mais velho lê com calma) e podem ser fechados
export function fecharToast(id: number) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

function mostrar(tipo: Toast['tipo'], texto: string, duracao = 8000) {
  const id = ++seq
  toasts.push({ id, tipo, texto })
  setTimeout(() => fecharToast(id), duracao)
}

export const toast = {
  sucesso: (t: string) => mostrar('sucesso', t),
  erro: (t: unknown) => mostrar('erro', t instanceof Error ? t.message : String(t), 12000),
  info: (t: string) => mostrar('info', t),
}
