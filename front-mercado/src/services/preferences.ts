/** Preferências guardadas só neste navegador: favoritos, produtores seguidos e tamanho da letra. */
import { reactive } from 'vue'

function lerLista(chave: string): number[] {
  try { return JSON.parse(localStorage.getItem(chave) || '[]') } catch { return [] }
}
function salvar(chave: string, lista: number[]) {
  try { localStorage.setItem(chave, JSON.stringify(lista)) } catch { /* sem armazenamento */ }
}

export type TamanhoLetra = 'normal' | 'grande' | 'maior'
const CLASSES_LETRA: Record<TamanhoLetra, string> = { normal: '', grande: 'letra-grande', maior: 'letra-maior' }

function lerLetra(): TamanhoLetra {
  try {
    const v = localStorage.getItem('mn_letra')
    return v === 'grande' || v === 'maior' ? v : 'normal'
  } catch { return 'normal' }
}

/** Aplica o tamanho da letra no site inteiro (a escala do Tailwind é toda em rem). */
export function aplicarLetra(t: TamanhoLetra) {
  const html = document.documentElement
  html.classList.remove('letra-grande', 'letra-maior')
  if (CLASSES_LETRA[t]) html.classList.add(CLASSES_LETRA[t])
}

export const prefs = reactive({
  favoritos: lerLista('mn_favoritos'),
  letra: lerLetra(),

  mudarLetra(t: TamanhoLetra) {
    this.letra = t
    aplicarLetra(t)
    try { localStorage.setItem('mn_letra', t) } catch { /* sem armazenamento */ }
  },
  seguindo: lerLista('mn_seguindo'),

  isFavorito(id: number) { return this.favoritos.includes(id) },
  alternarFavorito(id: number) {
    this.favoritos = this.isFavorito(id) ? this.favoritos.filter((x) => x !== id) : [...this.favoritos, id]
    salvar('mn_favoritos', this.favoritos)
  },
  isSeguindo(id: number) { return this.seguindo.includes(id) },
  alternarSeguir(id: number): boolean {
    const seguir = !this.isSeguindo(id)
    this.seguindo = seguir ? [...this.seguindo, id] : this.seguindo.filter((x) => x !== id)
    salvar('mn_seguindo', this.seguindo)
    return seguir
  },
})
