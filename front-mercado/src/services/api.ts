/**
 * Cliente HTTP do Mercado Nativo.
 * Todas as telas usam `api()` para falar com o FastAPI — assim o endereço do backend,
 * o token de login e o tratamento de erros ficam num lugar só.
 */
import { session } from './auth'

/**
 * Endereço do backend. Sem VITE_API_URL, usa o mesmo computador que serviu o site na porta 8000 —
 * assim o celular que abre http://192.168.x.x:5173 fala com http://192.168.x.x:8000 automaticamente.
 */
export const API_URL = (
  (import.meta.env.VITE_API_URL as string | undefined) ||
  `${window.location.protocol}//${window.location.hostname}:8000`
).replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

type AuthKind = 'producer' | 'admin' | null

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  form?: FormData
  auth?: AuthKind
  params?: Record<string, string | number | boolean | null | undefined>
}

/** Monta a URL completa de uma imagem enviada ao backend (/uploads/...) */
export function assetUrl(path?: string | null): string {
  if (!path) return ''
  if (/^(https?:|blob:|data:)/.test(path)) return path
  return `${API_URL}${path.startsWith('/') ? '' : '/'}${path}`
}

function mensagemDeErro(data: any, status: number): string {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const campo = detail[0]?.loc?.slice(-1)[0]
    return `Verifique o campo "${campo}": ${detail[0]?.msg ?? 'valor inválido'}`
  }
  if (status >= 500) return 'Erro no servidor. Verifique o terminal do backend.'
  return 'Não foi possível concluir a operação.'
}

export async function api<T = any>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = 'GET', body, form, auth = null, params } = options
  const url = new URL(`${API_URL}${path}`)
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
  })

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = auth === 'producer' ? session.producerToken : auth === 'admin' ? session.adminToken : null
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    })
  } catch {
    throw new ApiError(`Sem conexão com o servidor (${API_URL}). Inicie o backend com o arquivo iniciar_backend.bat.`, 0)
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && auth) {
      // Sessão expirada: limpa e volta para o login correspondente
      if (auth === 'producer') session.logoutProducer()
      else session.logoutAdmin()
      const destino = auth === 'admin' ? '/admin/login' : '/login-produtor'
      if (!window.location.pathname.startsWith(destino)) window.location.assign(destino)
    }
    throw new ApiError(mensagemDeErro(data, response.status), response.status)
  }
  return data as T
}
