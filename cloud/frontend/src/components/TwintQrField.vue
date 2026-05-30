<template>
  <div class="form-field twint-qr-field">
    <label>TWINT QR-Code</label>
    <template v-if="editMode && activeId">
      <div v-if="previewUrl" class="twint-qr-preview">
        <img :src="previewUrl" alt="TWINT QR-Code" />
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
          QR hochladen
        </v-btn>
        <v-btn
          v-if="hasTwintQr || previewUrl"
          type="button"
          color="error"
          variant="outlined"
          :disabled="busy"
          @click="$emit('remove')"
        >
          Entfernen
        </v-btn>
      </div>
      <small>PNG oder SVG, max. 500 KB. Wird sofort gespeichert (nicht über «Speichern»).</small>
    </template>
    <small v-else>Veranstaltung zuerst speichern, dann QR-Code hochladen.</small>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  editMode: Boolean,
  activeId: { type: Number, default: null },
  hasTwintQr: Boolean,
  previewUrl: { type: String, default: '' },
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
