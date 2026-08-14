<template>
  <div v-if="organisationId" class="org-screensaver-section">
    <div class="section-header">
      <h3>{{ t('organisations.screensaver.sectionTitle') }}</h3>
      <p class="muted small">{{ t('organisations.screensaver.sectionHint') }}</p>
    </div>

    <div class="toggle-row">
      <label for="org-screensaver-greyscale">{{ t('organisations.screensaver.greyscale') }}</label>
      <v-switch
        id="org-screensaver-greyscale"
        :model-value="greyscale"
        hide-details
        density="compact"
        :disabled="busy || loading"
        @update:model-value="saveGreyscale"
      />
    </div>
    <p class="muted small">{{ t('organisations.screensaver.greyscaleHint') }}</p>

    <p v-if="loading" class="muted small">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <p class="muted small count-line">
        {{ t('organisations.screensaver.count', { count: images.length, max: MAX_IMAGES }) }}
      </p>

      <div v-if="images.length" class="gallery-grid">
        <div v-for="img in images" :key="img.id" class="gallery-item">
          <img
            v-if="previewUrls[img.id]"
            :src="previewUrls[img.id]"
            :alt="t('organisations.screensaver.imageAlt')"
            class="gallery-thumb"
            :class="{ 'gallery-thumb--greyscale': greyscale }"
          />
          <div v-else class="gallery-thumb placeholder muted">{{ img.mime }}</div>
          <div class="gallery-meta">
            <code class="sha">{{ shortSha(img.sha256) }}</code>
            <v-btn
              color="error"
              size="small"
              variant="outlined"
              type="button"
              :disabled="busy"
              @click="removeImage(img.id)"
            >
              {{ t('common.delete') }}
            </v-btn>
          </div>
        </div>
      </div>
      <p v-else class="muted small">{{ t('organisations.screensaver.empty') }}</p>

      <div class="upload-row">
        <input
          ref="fileInput"
          type="file"
          class="file-input"
          accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
          :disabled="busy || images.length >= MAX_IMAGES"
          @change="onFile"
        />
        <v-btn
          color="primary"
          type="button"
          :disabled="busy || images.length >= MAX_IMAGES"
          @click="fileInput?.click()"
        >
          {{ t('organisations.screensaver.upload') }}
        </v-btn>
      </div>
      <small class="muted">{{ t('organisations.screensaver.uploadHint') }}</small>
      <p v-if="message" :class="messageIsError ? 'error-text' : 'muted'">{{ message }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch, apiJson } from '../api'
import { getErrorMessage } from '@/types/api'
import type { OrganisationRead } from '@/types/api'

const MAX_IMAGES = 10

interface ScreensaverImage {
  id: number
  sha256: string
  mime: string
  created_at?: string | null
}

const props = defineProps<{
  organisationId?: number | null
}>()

const { t } = useI18n()
const loading = ref(false)
const busy = ref(false)
const loadError = ref('')
const message = ref('')
const messageIsError = ref(false)
const images = ref<ScreensaverImage[]>([])
const greyscale = ref(false)
const previewUrls = reactive<Record<number, string>>({})
const fileInput = ref<HTMLInputElement | null>(null)

function shortSha(sha: string): string {
  return sha.length > 12 ? `${sha.slice(0, 12)}…` : sha
}

function clearPreviews() {
  for (const id of Object.keys(previewUrls)) {
    const key = Number(id)
    URL.revokeObjectURL(previewUrls[key])
    delete previewUrls[key]
  }
}

async function loadPreview(img: ScreensaverImage) {
  if (!props.organisationId || previewUrls[img.id]) return
  try {
    const res = await apiFetch(`/organisations/${props.organisationId}/screensaver-images/${img.id}`)
    if (!res.ok) return
    const blob = await res.blob()
    previewUrls[img.id] = URL.createObjectURL(blob)
  } catch {
    /* ignore preview errors */
  }
}

async function load() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  clearPreviews()
  try {
    images.value = await apiJson<ScreensaverImage[]>(
      `/organisations/${props.organisationId}/screensaver-images`,
    )
    const org = await apiJson<OrganisationRead>(`/organisations/${props.organisationId}`)
    greyscale.value = Boolean(org.screensaver_greyscale)
    await Promise.all(images.value.map((img) => loadPreview(img)))
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('organisations.screensaver.loadError'))
  } finally {
    loading.value = false
  }
}

async function saveGreyscale(value: boolean | null) {
  if (!props.organisationId) return
  greyscale.value = Boolean(value)
  busy.value = true
  message.value = ''
  messageIsError.value = false
  try {
    const data = await apiJson<OrganisationRead>(`/organisations/${props.organisationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ screensaver_greyscale: greyscale.value }),
    })
    greyscale.value = Boolean(data.screensaver_greyscale)
    message.value = t('organisations.screensaver.greyscaleSaved')
  } catch (e: unknown) {
    messageIsError.value = true
    message.value = getErrorMessage(e, t('organisations.screensaver.greyscaleSaveError'))
  } finally {
    busy.value = false
  }
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !props.organisationId) return
  if (images.value.length >= MAX_IMAGES) {
    messageIsError.value = true
    message.value = t('organisations.screensaver.maxReached')
    return
  }
  busy.value = true
  message.value = ''
  messageIsError.value = false
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await apiFetch(`/organisations/${props.organisationId}/screensaver-images`, {
      method: 'POST',
      body: form,
    })
    if (!res.ok) {
      const err = (await res.json().catch(() => ({}))) as {
        detail?: { message?: string } | string
      }
      const detail = err.detail
      const msg =
        typeof detail === 'string'
          ? detail
          : detail && typeof detail === 'object'
            ? detail.message
            : undefined
      throw new Error(msg || t('organisations.screensaver.uploadError'))
    }
    message.value = t('organisations.screensaver.uploaded')
    await load()
  } catch (e: unknown) {
    messageIsError.value = true
    message.value = e instanceof Error ? e.message : t('organisations.screensaver.uploadError')
  } finally {
    busy.value = false
  }
}

async function removeImage(imageId: number) {
  if (!props.organisationId) return
  if (!window.confirm(t('organisations.screensaver.deleteConfirm'))) return
  busy.value = true
  message.value = ''
  messageIsError.value = false
  try {
    const res = await apiFetch(
      `/organisations/${props.organisationId}/screensaver-images/${imageId}`,
      { method: 'DELETE' },
    )
    if (!res.ok && res.status !== 204) {
      throw new Error(t('organisations.screensaver.deleteError'))
    }
    message.value = t('organisations.screensaver.deleted')
    await load()
  } catch (e: unknown) {
    messageIsError.value = true
    message.value = e instanceof Error ? e.message : t('organisations.screensaver.deleteError')
  } finally {
    busy.value = false
  }
}

watch(
  () => props.organisationId,
  (id) => {
    if (id) void load()
    else {
      images.value = []
      greyscale.value = false
      clearPreviews()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  clearPreviews()
})
</script>

<style scoped>
.org-screensaver-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.section-header h3 {
  margin: 0 0 0.25rem;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: 0.75rem;
}

.gallery-item {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.gallery-thumb {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  border-radius: 4px;
  background: #f0f0f0;
}

.gallery-thumb.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
}

.gallery-thumb--greyscale {
  filter: grayscale(1);
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 28rem;
}

.gallery-meta {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  align-items: flex-start;
}

.sha {
  font-size: 0.7rem;
  word-break: break-all;
}

.file-input {
  display: none;
}

.upload-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.muted {
  color: rgba(0, 0, 0, 0.55);
}

.small {
  font-size: 0.875rem;
}

.error-text {
  color: #b00020;
}

.count-line {
  margin: 0;
}
</style>
