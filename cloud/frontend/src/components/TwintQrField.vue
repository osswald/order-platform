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
        <Button
          type="button"
          label="QR hochladen"
          class="secondary-button"
          :disabled="busy"
          @click="fileInput?.click()"
        />
        <Button
          v-if="hasTwintQr || previewUrl"
          type="button"
          label="Entfernen"
          class="danger"
          :disabled="busy"
          @click="$emit('remove')"
        />
      </div>
      <small>PNG oder SVG, max. 500 KB. Wird sofort gespeichert (nicht über «Speichern»).</small>
    </template>
    <small v-else>Veranstaltung zuerst speichern, dann QR-Code hochladen.</small>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'

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
  background: var(--p-surface-100);
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
