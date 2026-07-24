import type { Ref } from 'vue'
import { i18n } from '@/i18n'

function t(key: string): string {
  return i18n.global.t(key)
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  return false
}

export type ValidationRule = (value: unknown) => boolean | string

export const rules = {
  required: (value: unknown) => !isEmpty(value) || t('validation.required'),

  requiredArray: (value: unknown) =>
    (Array.isArray(value) && value.length > 0) || t('validation.required'),

  requiredDate: (value: unknown) =>
    (value instanceof Date && !Number.isNaN(value.getTime())) || t('validation.required'),

  requiredNumber: (value: unknown) => {
    if (value === null || value === undefined || value === '') return t('validation.required')
    const n = Number(value)
    return !Number.isNaN(n) || t('validation.required')
  },

  minNumber: (min: number) => (value: unknown) => {
    if (value === null || value === undefined || value === '') return t('validation.required')
    const n = Number(value)
    return (!Number.isNaN(n) && n >= min) || t('validation.required')
  },

  email: (value: unknown) => {
    if (isEmpty(value)) return t('validation.required')
    const s = String(value).trim()
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) || t('validation.invalidEmail')
  },

  passwordMatch: (other: unknown) => (value: unknown) =>
    value === other || t('validation.passwordMismatch'),

  minPasswordLength: (min = 10) => (value: unknown) => {
    if (isEmpty(value)) return t('validation.required')
    return String(value).length >= min || t('validation.passwordTooShort')
  },
}

interface FormValidateResult {
  valid: boolean
}

export interface ValidatableForm {
  validate: () => Promise<FormValidateResult>
}

/** Run v-form validate(); returns true when valid. */
export async function validateForm(formRef: Ref<ValidatableForm | null | undefined>): Promise<boolean> {
  if (!formRef?.value) return true
  const result = await formRef.value.validate()
  return result.valid
}
