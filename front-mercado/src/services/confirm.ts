/**
 * Janela de confirmação própria (substitui o confirm() do navegador, que tem letra pequena e
 * botões "OK/Cancelar" pouco claros). Uso:
 *   if (!(await confirmar({ titulo: 'Excluir produto?', texto: '...', sim: 'Sim, excluir', perigo: true }))) return
 */
import { reactive } from 'vue'

export interface PedidoConfirmacao {
  titulo: string; texto?: string; sim?: string; nao?: string; perigo?: boolean
  /** Mostra um campo para escrever o motivo (ex.: enviado ao vendedor pelo WhatsApp) */
  motivo?: { rotulo: string; placeholder?: string }
}

export const confirmacao = reactive<{ aberta: boolean; pedido: PedidoConfirmacao | null; texto: string; responder: (v: boolean) => void }>({
  aberta: false,
  pedido: null,
  texto: '',
  responder: () => {},
})

export function confirmar(pedido: PedidoConfirmacao): Promise<boolean> {
  return new Promise((resolve) => {
    confirmacao.pedido = pedido
    confirmacao.texto = ''
    confirmacao.aberta = true
    confirmacao.responder = (v: boolean) => {
      confirmacao.aberta = false
      resolve(v)
    }
  })
}

/** Igual ao confirmar(), mas devolve o motivo digitado ('' se vazio) ou null se a pessoa desistiu. */
export async function confirmarComMotivo(pedido: PedidoConfirmacao): Promise<string | null> {
  const ok = await confirmar(pedido)
  return ok ? confirmacao.texto.trim() : null
}
