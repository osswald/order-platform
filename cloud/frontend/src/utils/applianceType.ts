import { i18n } from '@/i18n'

export const APPLIANCE_TYPES = ['server', 'router', 'ap', 'printer', 'mobile', 'tablet'] as const

export type ApplianceType = (typeof APPLIANCE_TYPES)[number]

const APPLIANCE_TYPE_META: Record<
  ApplianceType,
  { icon: string; color: string }
> = {
  server: { icon: 'mdi-server', color: 'primary' },
  router: { icon: 'mdi-router-wireless', color: 'deep-purple' },
  ap: { icon: 'mdi-wifi', color: 'success' },
  printer: { icon: 'mdi-printer', color: 'warning' },
  mobile: { icon: 'mdi-cellphone', color: 'info' },
  tablet: { icon: 'mdi-tablet', color: 'teal' },
}

const DEFAULT_ICON = 'mdi-devices'
const DEFAULT_COLOR = 'default'

function t(key: string): string {
  return i18n.global.t(key)
}

function isApplianceType(type: string): type is ApplianceType {
  return (APPLIANCE_TYPES as readonly string[]).includes(type)
}

export function applianceTypeLabel(type: string): string {
  const key = `applianceType.${type}`
  const translated = t(key)
  return translated !== key ? translated : type
}

export function applianceTypeIcon(type: string): string {
  return isApplianceType(type) ? APPLIANCE_TYPE_META[type].icon : DEFAULT_ICON
}

export function applianceTypeColor(type: string): string {
  return isApplianceType(type) ? APPLIANCE_TYPE_META[type].color : DEFAULT_COLOR
}

/** Stable display/sort order index; unknown types sort after known ones. */
export function applianceTypeOrderIndex(type: string): number {
  const idx = (APPLIANCE_TYPES as readonly string[]).indexOf(type)
  return idx === -1 ? APPLIANCE_TYPES.length : idx
}

export function compareApplianceTypes(a: string, b: string): number {
  return applianceTypeOrderIndex(a) - applianceTypeOrderIndex(b)
}
