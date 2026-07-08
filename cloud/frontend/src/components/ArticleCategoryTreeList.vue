<template>
  <div class="article-category-tree-list">
    <v-text-field
      v-model="filter"
      :placeholder="filterPlaceholder"
      prepend-inner-icon="mdi-magnify"
      density="compact"
      hide-details
      clearable
      class="tree-filter"
    />
    <v-progress-linear v-if="loading" indeterminate color="primary" class="tree-loading" />
    <v-treeview
      v-else
      :items="filteredItems"
      item-value="key"
      item-title="title"
      item-children="children"
      open-all
      density="compact"
      class="article-tree"
    >
      <template #title="{ item, title }">
        <span
          :class="['tree-item-title', { 'tree-item-leaf': isLeaf(item) }]"
          :role="isLeaf(item) ? 'button' : undefined"
          :tabindex="isLeaf(item) ? 0 : undefined"
          :aria-label="isLeaf(item) ? leafAriaLabel(item, title) : undefined"
          @click.stop="onTitleClick(item, $event)"
          @keydown.enter.prevent="onTitleClick(item, $event)"
          @keydown.space.prevent="onTitleClick(item, $event)"
        >
          {{ nodeTitle(item, title) }}
        </span>
      </template>
    </v-treeview>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { articleTreeKeyToId, filterTreeNodes, type TreeViewNode } from '../utils/articleCategoryTree'

const props = withDefaults(
  defineProps<{
    items: TreeViewNode[]
    loading?: boolean
    filterPlaceholder?: string
    pickAriaLabel?: (title: string) => string
  }>(),
  {
    loading: false,
    filterPlaceholder: '',
    pickAriaLabel: undefined,
  },
)

const emit = defineEmits<{
  'pick-article': [articleId: number]
}>()

const filter = ref('')

const filteredItems = computed(() => {
  const q = filter.value.trim().toLowerCase()
  if (!q) return props.items
  return filterTreeNodes(props.items, q)
})

function isLeaf(item: TreeSlotItem): boolean {
  const children = item.children ?? item.raw?.children
  return !children?.length
}

type TreeSlotItem = TreeViewNode & { raw?: TreeViewNode }

function nodeTitle(item: TreeSlotItem, title?: string | number | boolean): string {
  if (typeof title === 'string' && title) return title
  if (item.title) return item.title
  return item.raw?.title || ''
}

function leafAriaLabel(item: TreeSlotItem, title?: string | number | boolean): string {
  const label = nodeTitle(item, title)
  if (props.pickAriaLabel) return props.pickAriaLabel(label)
  return label
}

function onTitleClick(item: TreeSlotItem, event: Event) {
  if (!isLeaf(item)) return
  event.preventDefault()
  const articleId = articleTreeKeyToId(item.key || item.raw?.key || '')
  if (articleId != null) emit('pick-article', articleId)
}
</script>

<style scoped>
.tree-filter {
  margin-bottom: 0.5rem;
}

.tree-loading {
  margin-bottom: 0.5rem;
}

.article-tree {
  max-height: 280px;
  overflow-y: auto;
}

.tree-item-leaf {
  cursor: pointer;
  border-radius: 4px;
}

.tree-item-leaf:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.tree-item-leaf:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
</style>
