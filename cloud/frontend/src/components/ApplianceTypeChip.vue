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

<script setup>
import {
  applianceTypeColor,
  applianceTypeIcon,
  applianceTypeLabel,
} from '../utils/applianceType'

defineProps({
  type: { type: String, required: true },
  size: { type: String, default: 'small' },
})
</script>
