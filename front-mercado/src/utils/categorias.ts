/**
 * Categorias de produto — lista única usada na vitrine, no cadastro de produto e no painel admin.
 * Precisa bater com CATEGORIAS em backend/app/models/product_model.py.
 */
export const CATEGORIAS = ['Hortifruti', 'Artesanato', 'Alimentos', 'Bebidas'] as const
export type Categoria = (typeof CATEGORIAS)[number]

/** Nome mais fácil de entender para quem compra */
export const NOME_CATEGORIA: Record<string, string> = {
  Todos: 'Tudo', Hortifruti: 'Frutas e verduras', Artesanato: 'Artesanato', Alimentos: 'Alimentos', Bebidas: 'Bebidas',
}

/** Desenho de cada categoria (nomes do components/ui/Icon.vue) */
export const ICONE_CATEGORIA: Record<string, string> = {
  Todos: 'grid', Hortifruti: 'sprout', Artesanato: 'basket', Alimentos: 'pot', Bebidas: 'cup',
}
