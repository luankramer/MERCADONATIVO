/**
 * Diminui fotos grandes antes de enviar (celular costuma gerar fotos de 4 a 12 MB).
 * Com internet fraca da zona rural, uma foto de ~300 KB sobe muito mais rápido.
 * Se o navegador não conseguir ler a imagem, devolve o arquivo original.
 */
export async function reduzirImagem(arquivo: File, ladoMaximo = 1600, qualidade = 0.82): Promise<File> {
  if (!arquivo.type.startsWith('image/') || arquivo.type === 'image/gif') return arquivo
  try {
    const bitmap = await createImageBitmap(arquivo)
    const escala = Math.min(1, ladoMaximo / Math.max(bitmap.width, bitmap.height))
    if (escala === 1 && arquivo.size < 900 * 1024) { bitmap.close(); return arquivo }
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * escala)
    canvas.height = Math.round(bitmap.height * escala)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/jpeg', qualidade))
    if (!blob || blob.size >= arquivo.size) return arquivo
    const nome = arquivo.name.replace(/\.[^.]+$/, '') + '.jpg'
    return new File([blob], nome, { type: 'image/jpeg', lastModified: Date.now() })
  } catch {
    return arquivo
  }
}
