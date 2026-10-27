/** Sessão do produtor e do administrador (tokens JWT guardados no navegador). */
import { reactive } from 'vue'

function ler(chave: string): string | null {
  try { return localStorage.getItem(chave) } catch { return null }
}
function gravar(chave: string, valor: string | null) {
  try {
    if (valor === null) localStorage.removeItem(chave)
    else localStorage.setItem(chave, valor)
  } catch { /* navegador sem armazenamento */ }
}

/**
 * Aceita apenas tokens JWT válidos e não expirados do perfil certo.
 * Isso descarta tokens antigos salvos pelo sistema anterior (ex.: "token_jwt_autenticado_mvp_123").
 */
export function tokenValido(token: string | null, role: 'producer' | 'admin'): boolean {
  if (!token) return false
  const partes = token.split('.')
  if (partes.length !== 3) return false
  try {
    const payload = JSON.parse(atob(partes[1]!.replace(/-/g, '+').replace(/_/g, '/')))
    return payload.role === role && typeof payload.exp === 'number' && payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

function tokenSalvo(chave: string, role: 'producer' | 'admin'): string | null {
  const token = ler(chave)
  if (token && !tokenValido(token, role)) {
    gravar(chave, null)
    return null
  }
  return token
}

export const session = reactive({
  producerToken: tokenSalvo('producer_token', 'producer'),
  adminToken: tokenSalvo('admin_token', 'admin'),
  adminEmail: ler('admin_email'),
  adminNome: ler('admin_nome'),
  adminSuper: ler('admin_super') === 'true',

  get isProducer() { return tokenValido(this.producerToken, 'producer') },
  get isAdmin() { return tokenValido(this.adminToken, 'admin') },

  loginProducer(token: string) {
    this.producerToken = token
    gravar('producer_token', token)
  },
  logoutProducer() {
    this.producerToken = null
    gravar('producer_token', null)
  },
  loginAdmin(data: { access_token: string; email: string; nome: string; is_super: boolean }) {
    this.adminToken = data.access_token
    this.adminEmail = data.email
    this.adminNome = data.nome
    this.adminSuper = data.is_super
    gravar('admin_token', data.access_token)
    gravar('admin_email', data.email)
    gravar('admin_nome', data.nome)
    gravar('admin_super', String(data.is_super))
  },
  logoutAdmin() {
    this.adminToken = null
    this.adminEmail = null
    this.adminNome = null
    this.adminSuper = false
    ;['admin_token', 'admin_email', 'admin_nome', 'admin_super'].forEach((k) => gravar(k, null))
  },
})
