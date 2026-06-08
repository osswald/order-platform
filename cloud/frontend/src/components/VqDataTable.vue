<template>
  <v-data-table
    v-bind="attrs"
    :items-per-page="resolvedItemsPerPage"
    :mobile-breakpoint="TABLE_MOBILE_BREAKPOINT"
    :class="tableClass"
  >
    <template v-for="(_, name) in slots" #[name]="slotProps">
      <slot :name="name" v-bind="slotProps ?? {}" />
    </template>
  </v-data-table>
</template>

<script setup>
import { computed, useAttrs, useSlots } from 'vue'
import { TABLE_MOBILE_BREAKPOINT } from '../constants/layout'

defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
const slots = useSlots()

const tableClass = computed(() => {
  const extra = attrs.class
  if (!extra) return 'vq-data-table'
  if (Array.isArray(extra)) return ['vq-data-table', ...extra]
  return ['vq-data-table', extra]
})

const resolvedItemsPerPage = computed(() => {
  if (attrs['items-per-page'] != null) return attrs['items-per-page']
  if (attrs.itemsPerPage != null) return attrs.itemsPerPage
  return -1
})
</script>
