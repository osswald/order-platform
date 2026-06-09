import { i18n } from '../i18n'

function t(key) {
  return i18n.global.t(key)
}

function isEmpty(value) {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  return false
}

export const rules = {
  required: (value) => !isEmpty(value) || t('validation.required'),

  requiredArray: (value) =>
    (Array.isArray(value) && value.length > 0) || t('validation.required'),

  requiredDate: (value) =>
    (value instanceof Date && !Number.isNaN(value.getTime())) || t('validation.required'),

  requiredNumber: (value) => {
    if (value === null || value === undefined || value === '') return t('validation.required')
    const n = Number(value)
    return (!Number.isNaN(n)) || t('validation.required')
  },

  minNumber: (min) => (value) => {
    if (value === null || value === undefined || value === '') return t('validation.required')
    const n = Number(value)
    return (!Number.isNaN(n) && n >= min) || t('validation.required')
  },

  email: (value) => {
    if (isEmpty(value)) return t('validation.required')
    const s = String(value).trim()
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) || t('validation.invalidEmail')
  },

  passwordMatch: (other) => (value) =>
    value === other || t('validation.passwordMismatch'),
}

/** Run v-form validate(); returns true when valid. */
export async function validateForm(formRef) {
  if (!formRef?.value) return true
  const result = await formRef.value.validate()
  return result.valid
}
