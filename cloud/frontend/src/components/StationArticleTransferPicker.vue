<template>
  <div class="station-article-transfer-picker" :class="{ disabled }">
    <div class="transfer-panel">
      <h4 class="panel-heading">{{ $t('events.config.availableArticles') }}</h4>
      <p v-if="!loading && !availableTree.length" class="muted empty-hint">
        {{ $t('events.config.noAvailableArticles') }}
      </p>
      <ArticleCategoryTreeList
        v-else
        :items="availableTree"
        :loading="loading"
        :filter-placeholder="$t('events.config.filterArticles')"
        :pick-aria-label="pickAriaLabel"
        @pick-article="addArticle"
      />
    </div>
    <div class="transfer-panel">
      <h4 class="panel-heading">{{ $t('events.config.selectedArticles') }}</h4>
      <template v-if="selectedGroups.length">
        <v-text-field
          v-model="selectedFilter"
          :placeholder="$t('events.config.filterArticles')"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          hide-details
          clearable
          class="tree-filter"
        />
        <p v-if="!filteredSelectedGroups.length" class="muted empty-hint">
          {{ $t('events.config.noSelectedArticlesMatch') }}
        </p>
        <v-list v-else v-model:opened="openedGroups" density="compact" class="selected-list">
          <v-list-group
            v-for="group in filteredSelectedGroups"
            :key="group.categoryId"
            :value="group.categoryId"
          >
          <template #activator="{ props: activatorProps }">
            <v-list-item v-bind="activatorProps" :title="group.categoryName" />
          </template>
          <v-list-item
            v-for="art in group.articles"
            :key="art.id"
            :data-testid="`selected-article-${art.id}`"
            :title="articleLabel(art)"
            class="selected-article-item"
            role="button"
            tabindex="0"
            :aria-label="removeAriaLabel(art)"
            @click="removeArticle(art.id)"
            @keydown.enter.prevent="removeArticle(art.id)"
            @keydown.space.prevent="removeArticle(art.id)"
          />
        </v-list-group>
        </v-list>
      </template>
      <p v-else class="muted empty-hint">
        {{ $t('events.config.noSelectedArticles') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ArticleCategoryTreeList from './ArticleCategoryTreeList.vue'
import {
  buildArticleCategoryTree,
  buildSelectedArticleGroups,
  filterSelectedArticleGroups,
  mapTreeNodes,
  partitionArticlesBySelection,
} from '../utils/articleCategoryTree'
import type { ArticleRead } from '@/types/api'

const props = withDefaults(
  defineProps<{
    articles?: ArticleRead[]
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    articles: () => [],
    loading: false,
    disabled: false,
  },
)

const articleIds = defineModel<number[]>({ default: () => [] })

const { t } = useI18n()

const openedGroups = ref<number[]>([])
const selectedFilter = ref('')

const availableArticles = computed(() =>
  partitionArticlesBySelection(props.articles, articleIds.value).available,
)

const availableTree = computed(() => mapTreeNodes(buildArticleCategoryTree(availableArticles.value)))

const selectedGroups = computed(() => buildSelectedArticleGroups(props.articles, articleIds.value))

const filteredSelectedGroups = computed(() =>
  filterSelectedArticleGroups(selectedGroups.value, selectedFilter.value),
)

watch(
  filteredSelectedGroups,
  (groups) => {
    openedGroups.value = groups.map((g) => g.categoryId)
  },
  { immediate: true },
)

function articleLabel(art: ArticleRead): string {
  return `${art.label} — ${art.name}`
}

function pickAriaLabel(title: string): string {
  return t('events.config.addArticleToStation', { article: title })
}

function removeAriaLabel(art: ArticleRead): string {
  return t('events.config.removeArticleFromStation', { article: articleLabel(art) })
}

function addArticle(id: number) {
  if (props.disabled || props.loading) return
  const ids = articleIds.value || []
  if (ids.includes(id)) return
  articleIds.value = [...ids, id]
}

function removeArticle(id: number) {
  if (props.disabled || props.loading) return
  articleIds.value = (articleIds.value || []).filter((x) => Number(x) !== Number(id))
}
</script>

<style scoped>
.station-article-transfer-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.station-article-transfer-picker.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.transfer-panel {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  padding: 0.75rem;
  min-height: 200px;
}

.panel-heading {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.empty-hint {
  margin: 0.5rem 0 0;
  font-size: 0.875rem;
}

.tree-filter {
  margin-bottom: 0.5rem;
}

.selected-list {
  max-height: 280px;
  overflow-y: auto;
}

.selected-article-item {
  cursor: pointer;
}

.selected-article-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}

@media (max-width: 768px) {
  .station-article-transfer-picker {
    grid-template-columns: 1fr;
  }
}
</style>
