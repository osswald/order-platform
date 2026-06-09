import { createI18n } from 'vue-i18n'
import de from '../locales/de.json'
import en from '../locales/en.json'

export const DEFAULT_LOCALE = 'de'
export const SUPPORTED_LOCALES = ['de', 'en']

export const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LOCALE,
  fallbackLocale: DEFAULT_LOCALE,
  messages: { de, en },
})

export function currentLocale() {
  return i18n.global.locale.value
}
