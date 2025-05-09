import { createRouter, createWebHistory } from 'vue-router'
import App from '../App.vue'
import ConfigPage from '../components/ConfigPage.vue'

const routes = [
  { path: '/', component: App },         // Main page route
  { path: '/config', component: ConfigPage }  // Config page route
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router