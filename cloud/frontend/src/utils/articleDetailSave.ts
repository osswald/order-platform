export type ArticleSaveStep = 'article' | 'additions' | 'ingredients'

export type ArticleSaveMode = 'create' | 'edit'

export type ArticleSaveDestination = {
  kind: 'detail'
  articleId: number
}

export type ArticleSaveSuccess = {
  ok: true
  articleId: number
  destination: ArticleSaveDestination
}

export type ArticleSaveFailure = {
  ok: false
  failedStep: ArticleSaveStep
  error: unknown
}

export type ArticleSaveResult = ArticleSaveSuccess | ArticleSaveFailure

export function planArticleSaveSteps(input: {
  mode: ArticleSaveMode
  isAddition: boolean
  ingredientsEnabled: boolean
}): ArticleSaveStep[] {
  if (input.mode === 'create') {
    return ['article']
  }
  const steps: ArticleSaveStep[] = ['article']
  if (!input.isAddition) {
    steps.push('additions')
  }
  if (input.ingredientsEnabled) {
    steps.push('ingredients')
  }
  return steps
}

export function articleSaveSuccessDestination(articleId: number): ArticleSaveDestination {
  return { kind: 'detail', articleId }
}

export async function runArticleSaveSequence(input: {
  mode: ArticleSaveMode
  isAddition: boolean
  ingredientsEnabled: boolean
  saveArticle: () => Promise<{ id: number }>
  saveAdditions: (articleId: number) => Promise<void>
  saveIngredients: (articleId: number) => Promise<void>
}): Promise<ArticleSaveResult> {
  const steps = planArticleSaveSteps({
    mode: input.mode,
    isAddition: input.isAddition,
    ingredientsEnabled: input.ingredientsEnabled,
  })

  let articleId: number | undefined

  for (const step of steps) {
    try {
      if (step === 'article') {
        const saved = await input.saveArticle()
        articleId = Number(saved.id)
      } else if (step === 'additions') {
        await input.saveAdditions(articleId!)
      } else {
        await input.saveIngredients(articleId!)
      }
    } catch (error: unknown) {
      return { ok: false, failedStep: step, error }
    }
  }

  return {
    ok: true,
    articleId: articleId!,
    destination: articleSaveSuccessDestination(articleId!),
  }
}
