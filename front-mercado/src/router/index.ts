import { createRouter, createWebHistory } from 'vue-router'
import { session } from '@/services/auth'
import CatalogView from '../views/CatalogView.vue'

/**
 * Rotas do Mercado Nativo
 *  - meta.produtor: exige login do produtor (WhatsApp)
 *  - meta.admin: exige login de administrador
 * As telas são carregadas sob demanda (import dinâmico) para o app abrir rápido no celular.
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    // ---------- Consumidor (público) ----------
    // A página inicial já é a vitrine, como nos outros marketplaces
    { path: '/', name: 'vitrine', component: CatalogView },
    { path: '/vitrine', redirect: (to) => ({ path: '/', query: to.query }) },
    { path: '/vitrine/produto/:id', name: 'produto', component: () => import('../views/ProductDetailView.vue') },
    { path: '/produtor/:id', name: 'produtor-publico', component: () => import('../views/ProducerPublicView.vue') },
    { path: '/pedido/:codigo', name: 'pedido', component: () => import('../views/OrderView.vue') },
    { path: '/ajuda', name: 'ajuda', component: () => import('../views/AjudaView.vue') },
    { path: '/politicas', redirect: '/politicas/privacidade' },
    { path: '/politicas/:slug', name: 'politicas', component: () => import('../views/PoliticasView.vue') },
    { path: '/privacidade', redirect: '/politicas/privacidade' },
    { path: '/termos', redirect: '/politicas/termos' },

    // ---------- Produtor ----------
    { path: '/login-produtor', name: 'login-produtor', component: () => import('../views/LoginProducerView.vue') },
    { path: '/cadastro-produtor', name: 'cadastro-produtor', component: () => import('../views/RegisterProducerView.vue') },
    { path: '/painel', name: 'painel', component: () => import('../views/ProducerDashboard.vue'), meta: { produtor: true } },
    { path: '/painel/produto/novo', name: 'novo-produto', component: () => import('../views/ProductForm.vue'), meta: { produtor: true } },
    { path: '/painel/produto/:id', name: 'editar-produto', component: () => import('../views/ProductForm.vue'), meta: { produtor: true } },
    { path: '/painel/perfil', name: 'perfil', component: () => import('../views/Perfil.vue'), meta: { produtor: true } },

    // ---------- Administração ----------
    { path: '/admin/login', name: 'admin-login', component: () => import('../views/LoginAdminView.vue') },
    {
      path: '/admin',
      component: () => import('../views/AdminDashboardView.vue'),
      meta: { admin: true },
      children: [
        { path: '', redirect: '/admin/visao-geral' },
        { path: 'visao-geral', name: 'admin-overview', component: () => import('../components/admin/OverviewTab.vue'), meta: { titulo: 'Visão Geral do Sistema' } },
        { path: 'aprovacoes', name: 'admin-approvals', component: () => import('../components/admin/ApprovalsTab.vue'), meta: { titulo: 'Curadoria de Publicações' } },
        { path: 'vitrine-premium', name: 'admin-premium', component: () => import('../components/admin/PremiumTab.vue'), meta: { titulo: 'Gestão de Vitrine e Destaques' } },
        { path: 'vendedores', name: 'admin-producers', component: () => import('../components/admin/ProducersTab.vue'), meta: { titulo: 'Vendedores Cadastrados' } },
        { path: 'administradores', name: 'admin-admins', component: () => import('../components/admin/AdminsTab.vue'), meta: { titulo: 'Gestão de Administradores' } },
      ],
    },

    // ---------- Endereços antigos (compatibilidade) ----------
    { path: '/catalogo', redirect: '/painel' },
    { path: '/perfil', redirect: '/painel/perfil' },
    { path: '/produto/novo', redirect: '/painel/produto/novo' },
    { path: '/produto/:id', redirect: (to) => `/painel/produto/${to.params.id}` },
    { path: '/admin/dashboard', redirect: '/admin/visao-geral' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.matched.some((r) => r.meta.produtor) && !session.isProducer) {
    return { path: '/login-produtor', query: { voltar: to.fullPath } }
  }
  if (to.matched.some((r) => r.meta.admin) && !session.isAdmin) {
    return { path: '/admin/login' }
  }
  if (to.path === '/admin/login' && session.isAdmin) return '/admin/visao-geral'
})

export default router
