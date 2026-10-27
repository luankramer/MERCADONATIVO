/**
 * "Ouvir": lê um texto em voz alta com a voz do próprio aparelho (Web Speech API).
 * Funciona sem internet e sem serviço externo; se o navegador não tiver voz, o botão nem aparece.
 */
import { ref } from 'vue'

export const falando = ref(false)
export const vozDisponivel = typeof window !== 'undefined' && 'speechSynthesis' in window

function vozPortugues(): SpeechSynthesisVoice | undefined {
  const vozes = window.speechSynthesis.getVoices()
  return vozes.find((v) => v.lang === 'pt-BR') || vozes.find((v) => v.lang.startsWith('pt'))
}

export function falar(texto: string) {
  if (!vozDisponivel) return
  window.speechSynthesis.cancel()
  const fala = new SpeechSynthesisUtterance(texto)
  fala.lang = 'pt-BR'
  fala.rate = 0.9 // um pouco mais devagar
  const voz = vozPortugues()
  if (voz) fala.voice = voz
  fala.onend = () => (falando.value = false)
  fala.onerror = () => (falando.value = false)
  falando.value = true
  window.speechSynthesis.speak(fala)
}

export function pararFala() {
  if (vozDisponivel) window.speechSynthesis.cancel()
  falando.value = false
}
