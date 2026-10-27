/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // Escala de letra maior que a padrão do Tailwind: o público é mais velho.
      // Tudo em rem, então o botão "Tamanho da letra" (A+) aumenta o site inteiro junto.
      fontSize: {
        xs: ['0.875rem', { lineHeight: '1.3rem' }],     // 14px (era 12px) — menor tamanho permitido
        sm: ['1rem', { lineHeight: '1.5rem' }],         // 16px (era 14px)
        base: ['1.125rem', { lineHeight: '1.7rem' }],   // 18px (era 16px) — texto normal
        lg: ['1.25rem', { lineHeight: '1.8rem' }],      // 20px
        xl: ['1.375rem', { lineHeight: '1.9rem' }],     // 22px
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Paleta do Mercado Nativo (protótipos do Figma)
        nativo: { DEFAULT: '#0B6B4A', dark: '#08533A', light: '#E3F4EC', soft: '#F1FAF5' },
        terra: { DEFAULT: '#9A4A1E', dark: '#7A3A16', light: '#FDF3E7', border: '#F3CBA5', button: '#FBE7C6' },
        // Destaque/Premium usa a mesma terracota da marca (antes era um laranja diferente)
        destaque: { DEFAULT: '#9A4A1E', light: '#FBE7C6' },
        painel: { DEFAULT: '#0B0F19', side: '#050814', item: '#1E2433' },
        brand: { light: '#f5f5f4', DEFAULT: '#78716c', dark: '#44403c' },
      },
    },
  },
  plugins: [],
}
