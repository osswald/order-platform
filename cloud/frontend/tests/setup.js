import { createI18n } from 'vue-i18n'
import { config } from '@vue/test-utils'
import de from '../src/locales/de.json'
import en from '../src/locales/en.json'

function createStorage() {
  let data = {}
  return {
    getItem(key) {
      return key in data ? data[key] : null
    },
    setItem(key, value) {
      data[key] = String(value)
    },
    removeItem(key) {
      delete data[key]
    },
    clear() {
      data = {}
    },
  }
}

globalThis.localStorage = createStorage()
globalThis.sessionStorage = createStorage()

export const testI18n = createI18n({
  legacy: false,
  locale: 'de',
  fallbackLocale: 'de',
  messages: { de, en },
})

config.global.plugins = [testI18n]
