// i18n 設定檔 — vue-i18n v11
// 支援語言：zh-TW（繁體中文）、id（印尼文）
import { createI18n } from 'vue-i18n'
import zhTW from './zh-TW.json'
import id from './id.json'

// 從 localStorage 讀取使用者偏好語言，預設繁體中文
const savedLocale = localStorage.getItem('ktw-admin-locale') || 'zh-TW'

const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: savedLocale,
  fallbackLocale: 'zh-TW',
  messages: {
    'zh-TW': zhTW,
    'id': id,
  },
})

// 切換語言並持久化
export function setLocale(locale) {
  i18n.global.locale.value = locale
  localStorage.setItem('ktw-admin-locale', locale)
  document.documentElement.setAttribute('lang', locale)
}

export default i18n
