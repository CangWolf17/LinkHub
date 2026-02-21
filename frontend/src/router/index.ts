import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/software',
        },
        {
          path: 'software',
          name: 'Software',
          component: () => import('@/views/SoftwareView.vue'),
        },
        {
          path: 'workspaces',
          name: 'Workspaces',
          component: () => import('@/views/WorkspaceView.vue'),
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/SettingsView.vue'),
        },
      ],
    },
  ],
})

export default router
