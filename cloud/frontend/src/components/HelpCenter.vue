<template>
  <section class="vq-page help-center">
    <div class="vq-page-header">
      <div>
        <h1>Hilfe</h1>
        <p>Anleitungen und Erklärungen zur Vendiqo Cloud-Verwaltung.</p>
      </div>
    </div>

    <v-text-field
      v-model="searchQuery"
      label="Suchen"
      placeholder="Stichwort eingeben…"
      prepend-inner-icon="mdi-magnify"
      hide-details
      clearable
      class="help-search"
    />

    <p v-if="notFound" class="error help-not-found">
      Artikel «{{ routeSlug }}» wurde nicht gefunden.
      <RouterLink :to="{ name: 'help' }">Zurück zur Übersicht</RouterLink>
    </p>

    <template v-else-if="showArticleView && currentArticle">
      <nav class="help-breadcrumb" aria-label="Hilfe-Navigation">
        <RouterLink :to="{ name: 'help' }">Hilfe</RouterLink>
        <span aria-hidden="true">/</span>
        <span>{{ currentArticle.categoryTitle }}</span>
      </nav>

      <EventConfigLayout
        :mobile="isMobile"
        v-model:active-tab="activeSlug"
        :sections="navSections"
      >
        <template v-for="article in categoryArticles" :key="article.slug" #[article.slug]>
          <div v-if="articleBodies[article.slug]" class="help-article">
            <h2 class="help-article-title">{{ articleBodies[article.slug].title }}</h2>
            <p class="help-article-summary">{{ articleBodies[article.slug].summary }}</p>
            <HelpMarkdown :html="articleBodies[article.slug].html" />
          </div>
        </template>
      </EventConfigLayout>
    </template>

    <div v-else class="help-index">
      <p v-if="filteredArticles.length === 0" class="muted-hint">
        Keine Artikel für «{{ searchQuery }}» gefunden.
      </p>

      <div v-for="category in visibleCategories" :key="category.id" class="help-category">
        <h2 class="help-category-title">{{ category.title }}</h2>
        <v-list density="compact" class="help-article-list">
          <v-list-item
            v-for="article in category.articles"
            :key="article.slug"
            :to="{ name: 'help-article', params: { slug: article.slug } }"
            :title="article.title"
            :subtitle="article.summary"
            prepend-icon="mdi-file-document-outline"
          />
        </v-list>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EventConfigLayout from './EventConfigLayout.vue'
import HelpMarkdown from './HelpMarkdown.vue'
import { useBreakpoint } from '../composables/useBreakpoint'
import {
  getArticle,
  getArticlesInCategory,
  getCategories,
  searchArticles,
} from '../utils/helpArticles.js'

const route = useRoute()
const router = useRouter()
const { matches: isMobile } = useBreakpoint(768)

const searchQuery = ref('')
const routeSlug = computed(() => route.params.slug ?? '')
const currentArticle = computed(() => (routeSlug.value ? getArticle(routeSlug.value) : null))
const notFound = computed(() => routeSlug.value && !currentArticle.value)

const showArticleView = computed(() => !!routeSlug.value && !!currentArticle.value)

const activeSlug = computed({
  get() {
    return routeSlug.value || ''
  },
  set(slug) {
    if (slug && slug !== routeSlug.value) {
      router.push({ name: 'help-article', params: { slug } })
    }
  },
})

const categoryArticles = computed(() => {
  if (!currentArticle.value) return []
  return getArticlesInCategory(currentArticle.value.categoryId)
})

const articleBodies = computed(() => {
  const bodies = {}
  for (const article of categoryArticles.value) {
    const loaded = getArticle(article.slug)
    if (loaded) bodies[article.slug] = loaded
  }
  return bodies
})

const navSections = computed(() =>
  categoryArticles.value.map((article) => ({
    id: article.slug,
    title: article.title,
    defaultOpen: article.slug === currentArticle.value?.slug,
  })),
)

const filteredArticles = computed(() => searchArticles(searchQuery.value))

const visibleCategories = computed(() => {
  const slugs = new Set(filteredArticles.value.map((article) => article.slug))
  return getCategories()
    .map((category) => ({
      ...category,
      articles: category.articles.filter((article) => slugs.has(article.slug)),
    }))
    .filter((category) => category.articles.length > 0)
})

watch(
  () => route.name,
  (name) => {
    if (name === 'help') {
      searchQuery.value = ''
    }
  },
)
</script>

<style scoped>
.help-search {
  max-width: 28rem;
  margin-bottom: 1.5rem;
}

.help-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

.help-breadcrumb a {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}

.help-breadcrumb a:hover {
  text-decoration: underline;
}

.help-category + .help-category {
  margin-top: 1.5rem;
}

.help-category-title {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.help-article-title {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}

.help-article-summary {
  margin: 0 0 1.25rem;
  opacity: 0.75;
}

.help-not-found a {
  margin-left: 0.35rem;
  color: rgb(var(--v-theme-primary));
}

.muted-hint {
  opacity: 0.7;
}
</style>
