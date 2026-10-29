/**
 * SAC do Mercado Nativo: contatos da equipe (front-mercado/.env).
 *   VITE_SUPORTE_WHATSAPP=68999999999   (só números, com DDD)
 *   VITE_SUPORTE_TELEFONE=6833334444
 *   VITE_SUPORTE_EMAIL=contato@exemplo.com
 * O que não estiver preenchido simplesmente não aparece na tela.
 */
import { telefone } from '@/utils/format'

const so = (v: unknown) => String(v || '').replace(/\D/g, '')

export const SAC_WHATSAPP = so(import.meta.env.VITE_SUPORTE_WHATSAPP)
export const SAC_TELEFONE = so(import.meta.env.VITE_SUPORTE_TELEFONE)
export const SAC_EMAIL = String(import.meta.env.VITE_SUPORTE_EMAIL || '').trim()

export const temSac = Boolean(SAC_WHATSAPP || SAC_TELEFONE || SAC_EMAIL)

/** Link do WhatsApp da equipe com uma mensagem pronta. */
export function linkWhatsappSac(mensagem = 'Olá! Preciso de ajuda com o Mercado Nativo.'): string {
  return SAC_WHATSAPP ? `https://wa.me/55${SAC_WHATSAPP}?text=${encodeURIComponent(mensagem)}` : ''
}

export function linkEmailSac(assunto = 'Atendimento Mercado Nativo', corpo = ''): string {
  if (!SAC_EMAIL) return ''
  const q = new URLSearchParams({ subject: assunto, ...(corpo ? { body: corpo } : {}) }).toString().replace(/\+/g, '%20')
  return `mailto:${SAC_EMAIL}?${q}`
}

export const linkTelefoneSac = SAC_TELEFONE ? `tel:+55${SAC_TELEFONE}` : ''
export const telefoneSacFormatado = telefone(SAC_TELEFONE)
export const whatsappSacFormatado = telefone(SAC_WHATSAPP)
