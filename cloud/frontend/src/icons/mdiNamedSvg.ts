import { h } from 'vue'
import type { IconProps, IconSet } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { mdiIconPaths } from './mdiIconPaths'

/**
 * Vuetify icon set that resolves template `mdi-*` names to curated `@mdi/js` SVG paths.
 */
export const mdiNamedSvg: IconSet = {
  component: (props: IconProps) => {
    const icon =
      typeof props.icon === 'string' && props.icon.startsWith('mdi-')
        ? (mdiIconPaths[props.icon] ?? props.icon)
        : props.icon
    return h(mdi.component, { ...props, icon })
  },
}

export { aliases as mdiSvgAliases }
