const MSG = 'Pflichtfeld'

function isEmpty(value) {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  return false
}

export const rules = {
  required: (value) => !isEmpty(value) || MSG,

  requiredArray: (value) =>
    (Array.isArray(value) && value.length > 0) || MSG,

  requiredDate: (value) =>
    (value instanceof Date && !Number.isNaN(value.getTime())) || MSG,

  requiredNumber: (value) => {
    if (value === null || value === undefined || value === '') return MSG
    const n = Number(value)
    return (!Number.isNaN(n)) || MSG
  },

  minNumber: (min) => (value) => {
    if (value === null || value === undefined || value === '') return MSG
    const n = Number(value)
    return (!Number.isNaN(n) && n >= min) || MSG
  },

  email: (value) => {
    if (isEmpty(value)) return MSG
    const s = String(value).trim()
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) || 'Ungültige E-Mail-Adresse'
  },

  passwordMatch: (other) => (value) =>
    value === other || 'Passwörter stimmen nicht überein',
}

/** Run v-form validate(); returns true when valid. */
export async function validateForm(formRef) {
  if (!formRef?.value) return true
  const result = await formRef.value.validate()
  return result.valid
}
