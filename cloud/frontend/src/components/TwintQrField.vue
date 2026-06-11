<template>
  <div class="form-field twint-qr-field">
    <label>{{ t('twint.label') }}</label>
    <template v-if="editMode && activeId">
      <div v-if="previewLoading" class="twint-qr-preview twint-qr-preview--loading">
        <v-progress-circular indeterminate color="primary" size="32" />
      </div>
      <div v-else-if="previewUrl" class="twint-qr-preview">
        <img :src="previewUrl" :alt="t('twint.alt')" />
      </div>
      <input
        ref="fileInput"
        type="file"
        class="twint-qr-file-input"
        accept="image/png,image/svg+xml,.png,.svg"
        @change="onFileChange"
      />
      <div class="twint-qr-actions">
        <v-btn
          type="button"
          variant="outlined"
          :disabled="busy"
          @click="fileInput?.click()"
        >
          {{ t('twint.upload') }}
        </v-btn>
        <v-btn
          v-if="hasTwintQr || previewUrl"
          type="button"
          color="error"
          variant="outlined"
          :disabled="busy"
          @click="$emit('remove')"
        >
          {{ t('twint.remove') }}
        </v-btn>
      </div>
      <small>{{ t('twint.hint') }}</small>
    </template>
    <small v-else>{{ t('twint.saveFirst') }}</small>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  editMode: Boolean,
  activeId: { type: Number, default: null },
  hasTwintQr: Boolean,
  previewUrl: { type: String, default: '' },
  previewLoading: Boolean,
  busy: Boolean,
})

const emit = defineEmits(['upload', 'remove'])

const fileInput = ref(null)

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (file) emit('upload', file)
  event.target.value = ''
}
</script>

<style scoped>
.twint-qr-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 5rem;
  padding: 0.75rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
}

.twint-qr-preview img {
  max-width: 220px;
  max-height: 220px;
  object-fit: contain;
}

.twint-qr-file-input {
  display: none;
}

.twint-qr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
</style>
