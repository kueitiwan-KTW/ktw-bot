// ktw-admin-web 進入點
import { createApp } from 'vue'
import App from './App.vue'
import i18n from './i18n/index.js'
import './style.css'

const app = createApp(App)
app.use(i18n)
app.mount('#app')
