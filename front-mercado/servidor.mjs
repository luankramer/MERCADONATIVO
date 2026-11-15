/**
 * Servidor do site já compilado (pasta dist) para publicar no Railway ou em qualquer servidor Node.
 * Não precisa de pacotes extras. Rotas como /produto/3 devolvem o index.html (o Vue Router cuida da tela).
 *
 * Uso:  npm run build  e depois  npm start   (porta: variável PORT, padrão 4173)
 */
import { createReadStream } from 'node:fs'
import { readFile, stat } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { brotliCompressSync, constants, gzipSync } from 'node:zlib'

const PASTA = resolve(fileURLToPath(new URL('.', import.meta.url)), 'dist')
const PORTA = Number(process.env.PORT) || 4173

const TIPOS = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
}

// Tipos de texto que valem a pena comprimir (JS, CSS, HTML, SVG...). Fotos já vêm comprimidas.
const COMPRIMIVEIS = new Set(['.html', '.js', '.mjs', '.css', '.json', '.webmanifest', '.svg', '.txt'])
const cacheComprimido = new Map() // "caminho|br" -> Buffer (os arquivos do build não mudam)

const SEGURANCA = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
}

/** Caminho do arquivo pedido, sempre dentro da pasta dist (bloqueia ../). */
function caminhoSeguro(url) {
  let rota
  try {
    rota = decodeURIComponent(new URL(url, 'http://local').pathname)
  } catch {
    return null
  }
  const arquivo = normalize(join(PASTA, rota))
  return arquivo === PASTA || arquivo.startsWith(PASTA + sep) ? arquivo : null
}

async function arquivoExiste(caminho) {
  try {
    return (await stat(caminho)).isFile()
  } catch {
    return false
  }
}

async function comprimido(caminho, codificacao) {
  const chave = `${caminho}|${codificacao}`
  if (!cacheComprimido.has(chave)) {
    const conteudo = await readFile(caminho)
    cacheComprimido.set(chave, codificacao === 'br'
      ? brotliCompressSync(conteudo, { params: { [constants.BROTLI_PARAM_QUALITY]: 9 } })
      : gzipSync(conteudo, { level: 9 }))
  }
  return cacheComprimido.get(chave)
}

async function enviar(req, res, caminho, cache) {
  const ext = extname(caminho).toLowerCase()
  const cabecalhos = {
    ...SEGURANCA,
    'Content-Type': TIPOS[ext] || 'application/octet-stream',
    'Cache-Control': cache,
    Vary: 'Accept-Encoding',
  }
  const aceita = String(req.headers['accept-encoding'] || '')
  const codificacao = !COMPRIMIVEIS.has(ext) ? null : /\bbr\b/.test(aceita) ? 'br' : /\bgzip\b/.test(aceita) ? 'gzip' : null
  if (codificacao) {
    const corpo = await comprimido(caminho, codificacao)
    res.writeHead(200, { ...cabecalhos, 'Content-Encoding': codificacao, 'Content-Length': corpo.length })
    return res.end(req.method === 'HEAD' ? undefined : corpo)
  }
  res.writeHead(200, cabecalhos)
  if (req.method === 'HEAD') return res.end()
  createReadStream(caminho).pipe(res)
}

const servidor = createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { ...SEGURANCA, Allow: 'GET, HEAD' })
    return res.end()
  }
  const caminho = caminhoSeguro(req.url || '/')
  if (!caminho) {
    res.writeHead(400, SEGURANCA)
    return res.end()
  }
  if (await arquivoExiste(caminho)) {
    // Arquivos com hash no nome (pasta assets) podem ficar em cache por 1 ano
    const fixo = caminho.includes(`${sep}assets${sep}`)
    return enviar(req, res, caminho, fixo ? 'public, max-age=31536000, immutable' : 'no-cache')
  }
  if (extname(caminho)) {
    // Pediu um arquivo (.png, .js...) que não existe: 404 de verdade
    res.writeHead(404, SEGURANCA)
    return res.end()
  }
  // Rota do Vue (ex.: /produto/3): devolve o index.html
  return enviar(req, res, join(PASTA, 'index.html'), 'no-cache')
})

servidor.listen(PORTA, '0.0.0.0', () => {
  console.log(`Mercado Nativo (site) no ar na porta ${PORTA}`)
})
