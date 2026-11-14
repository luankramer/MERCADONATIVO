/**
 * Servidor do site já compilado (pasta dist) para publicar no Railway ou em qualquer servidor Node.
 * Não precisa de pacotes extras. Rotas como /produto/3 devolvem o index.html (o Vue Router cuida da tela).
 *
 * Uso:  npm run build  e depois  npm start   (porta: variável PORT, padrão 4173)
 */
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

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

function enviar(res, caminho, cache) {
  res.writeHead(200, {
    ...SEGURANCA,
    'Content-Type': TIPOS[extname(caminho).toLowerCase()] || 'application/octet-stream',
    'Cache-Control': cache,
  })
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
    return enviar(res, caminho, fixo ? 'public, max-age=31536000, immutable' : 'no-cache')
  }
  if (extname(caminho)) {
    // Pediu um arquivo (.png, .js...) que não existe: 404 de verdade
    res.writeHead(404, SEGURANCA)
    return res.end()
  }
  // Rota do Vue (ex.: /produto/3): devolve o index.html
  enviar(res, join(PASTA, 'index.html'), 'no-cache')
})

servidor.listen(PORTA, '0.0.0.0', () => {
  console.log(`Mercado Nativo (site) no ar na porta ${PORTA}`)
})
