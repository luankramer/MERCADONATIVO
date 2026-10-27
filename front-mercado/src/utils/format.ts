export function moeda(valor: number | string | null | undefined): string {
  const n = Number(valor ?? 0)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/** (68) 9 9911-2233 */
export function telefone(valor?: string | null): string {
  let d = (valor || '').replace(/\D/g, '')
  if (d.startsWith('55') && d.length > 11) d = d.slice(2)
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d[2]} ${d.slice(3, 7)}-${d.slice(7)}`
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return valor || ''
}

/** Máscara enquanto digita */
export function mascaraTelefone(valor: string): string {
  const d = valor.replace(/\D/g, '').slice(0, 11)
  if (d.length <= 2) return d ? `(${d}` : ''
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return `(${d.slice(0, 2)}) ${d[2]} ${d.slice(3, 7)}-${d.slice(7)}`
}

export function mascaraCep(valor: string): string {
  const d = valor.replace(/\D/g, '').slice(0, 8)
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d
}

export function mascaraDocumento(valor: string): string {
  const d = valor.replace(/\D/g, '').slice(0, 14)
  if (d.length <= 11) {
    return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2')
  }
  return d.replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2')
}

export function iniciais(nome?: string | null): string {
  return (nome || '?').split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')
}

export function dataHora(iso?: string | null): string {
  if (!iso) return '-'
  return new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Busca endereço pelo CEP (ViaCEP) */
export async function buscarCep(cep: string): Promise<{ endereco: string; cidade: string; uf: string } | null> {
  const d = cep.replace(/\D/g, '')
  if (d.length !== 8) return null
  try {
    const r = await fetch(`https://viacep.com.br/ws/${d}/json/`)
    const j = await r.json()
    if (j.erro) return null
    const endereco = [j.logradouro, j.bairro].filter(Boolean).join(', ')
    return { endereco, cidade: j.localidade, uf: j.uf }
  } catch {
    return null
  }
}
