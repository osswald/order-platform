<template>
  <template v-if="variant === 'link'">
    <RouterLink class="help-link" :to="articleRoute" :aria-label="ariaLabel">
      {{ label }}
    </RouterLink>
  </template>

  <template v-else-if="variant === 'icon'">
    <v-btn
      :to="articleRoute"
      icon="mdi-help-circle-outline"
      :aria-label="ariaLabel"
      :size="size"
    />
  </template>

  <template v-else-if="variant === 'dialog'">
    <v-btn
      icon="mdi-help-circle-outline"
      :aria-label="ariaLabel"
      :size="size"
      @click="dialogOpen = true"
    />
    <v-dialog v-model="dialogOpen" max-width="40rem">
      <v-card v-if="article">
        <v-card-title>{{ article.title }}</v-card-title>
        <v-card-text>
          <p class="help-link-summary">{{ article.summary }}</p>
          <HelpMarkdown :html="article.html" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialogOpen = false">{{ $t('common.close') }}</v-btn>
          <v-btn color="primary" :to="articleRoute" @click="dialogOpen = false">
            {{ $t('help.fullGuide') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </template>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import HelpMarkdown from './HelpMarkdown.vue'
import { getArticle } from '../utils/helpArticles.js'
import { i18n } from '../i18n'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    slug: string
    label?: string
    variant?: 'link' | 'icon' | 'dialog'
    size?: string
  }>(),
  {
    label: () => i18n.global.t('help.title'),
    variant: 'icon',
    size: 'small',
  },
)

const dialogOpen = ref(false)

const article = computed(() => getArticle(props.slug))

const articleRoute = computed(() => ({
  name: 'help-article',
  params: { slug: props.slug },
}))

const ariaLabel = computed(() => {
  if (article.value?.title) return t('help.ariaLabel', { title: article.value.title })
  return props.label
})
</script>

<style scoped>
.help-link {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
  font-weight: 600;
}

.help-link:hover {
  text-decoration: underline;
}

.help-link-summary {
  margin: 0 0 1rem;
  opacity: 0.8;
}
</style>
