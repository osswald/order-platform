<template>
  <v-chip
    :color="applianceTypeColor(type)"
    :size="size"
    variant="tonal"
    :prepend-icon="applianceTypeIcon(type)"
  >
    {{ applianceTypeLabel(type) }}
  </v-chip>
</template>

<script setup lang="ts">
import {
  applianceTypeColor,
  applianceTypeIcon,
  applianceTypeLabel,
} from '../utils/applianceType'

withDefaults(
  defineProps<{
    type: string
    size?: string
  }>(),
  { size: 'small' },
)
</script>
