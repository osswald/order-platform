import { helpCategories as deCategories } from './helpIndex.de.js'
import { helpCategories as enCategories } from './helpIndex.en.js'
import { currentLocale } from '../../i18n'

export function getHelpCategories() {
  return currentLocale() === 'en' ? enCategories : deCategories
}

/** @deprecated Use getHelpCategories() for locale-aware index. */
export const helpCategories = deCategories
