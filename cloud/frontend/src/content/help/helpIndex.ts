import { helpCategories as deCategories } from './helpIndex.de'
import { helpCategories as enCategories } from './helpIndex.en'
import { currentLocale } from '../../i18n'

export function getHelpCategories() {
  return currentLocale() === 'en' ? enCategories : deCategories
}

/** @deprecated Use getHelpCategories() for locale-aware index. */
export const helpCategories = deCategories
