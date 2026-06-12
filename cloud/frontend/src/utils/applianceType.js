import { i18n } from '../i18n'

export const APPLIANCE_TYPES = ['server', 'printer', 'mobile', 'tablet', 'router', 'ap']

const APPLIANCE_TYPE_META = {
  server: { icon: 'mdi-server', color: 'primary' },
  printer: { icon: 'mdi-printer', color: 'warning' },
  mobile: { icon: 'mdi-cellphone', color: 'info' },
  tablet: { icon: 'mdi-tablet', color: 'teal' },
  router: { icon: 'mdi-router-wireless', color: 'deep-purple' },
  ap: { icon: 'mdi-wifi', color: 'success' },
}

const DEFAULT_ICON = 'mdi-devices'
const DEFAULT_COLOR = 'default'

function t(key) {
  return i18n.global.t(key)
}

export function applianceTypeLabel(type) {
  const key = `applianceType.${type}`
  const translated = t(key)
  return translated !== key ? translated : type
}

export function applianceTypeIcon(type) {
  return APPLIANCE_TYPE_META[type]?.icon ?? DEFAULT_ICON
}

export function applianceTypeColor(type) {
  return APPLIANCE_TYPE_META[type]?.color ?? DEFAULT_COLOR
}
