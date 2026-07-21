import { describe, expect, it, vi } from 'vitest'
import {
  articleSaveSuccessDestination,
  planArticleSaveSteps,
  runArticleSaveSequence,
} from './articleDetailSave'

describe('planArticleSaveSteps', () => {
  it('runs only the article step on create', () => {
    expect(
      planArticleSaveSteps({
        mode: 'create',
        isAddition: false,
        ingredientsEnabled: true,
      }),
    ).toEqual(['article'])
  })

  it('includes additions and ingredients on edit when both apply', () => {
    expect(
      planArticleSaveSteps({
        mode: 'edit',
        isAddition: false,
        ingredientsEnabled: true,
      }),
    ).toEqual(['article', 'additions', 'ingredients'])
  })

  it('skips additions when the article is an addition', () => {
    expect(
      planArticleSaveSteps({
        mode: 'edit',
        isAddition: true,
        ingredientsEnabled: true,
      }),
    ).toEqual(['article', 'ingredients'])
  })

  it('skips ingredients when the organisation feature is disabled', () => {
    expect(
      planArticleSaveSteps({
        mode: 'edit',
        isAddition: false,
        ingredientsEnabled: false,
      }),
    ).toEqual(['article', 'additions'])
  })
})

describe('articleSaveSuccessDestination', () => {
  it('always stays on article detail for create and update', () => {
    expect(articleSaveSuccessDestination(42)).toEqual({ kind: 'detail', articleId: 42 })
  })
})

describe('runArticleSaveSequence', () => {
  it('creates an article and destinations to its detail without link saves', async () => {
    const saveArticle = vi.fn().mockResolvedValue({ id: 99 })
    const saveAdditions = vi.fn()
    const saveIngredients = vi.fn()

    const result = await runArticleSaveSequence({
      mode: 'create',
      isAddition: false,
      ingredientsEnabled: true,
      saveArticle,
      saveAdditions,
      saveIngredients,
    })

    expect(result).toEqual({
      ok: true,
      articleId: 99,
      destination: { kind: 'detail', articleId: 99 },
    })
    expect(saveArticle).toHaveBeenCalledOnce()
    expect(saveAdditions).not.toHaveBeenCalled()
    expect(saveIngredients).not.toHaveBeenCalled()
  })

  it('updates article then applicable links and stays on detail', async () => {
    const saveArticle = vi.fn().mockResolvedValue({ id: 7 })
    const saveAdditions = vi.fn().mockResolvedValue(undefined)
    const saveIngredients = vi.fn().mockResolvedValue(undefined)

    const result = await runArticleSaveSequence({
      mode: 'edit',
      isAddition: false,
      ingredientsEnabled: true,
      saveArticle,
      saveAdditions,
      saveIngredients,
    })

    expect(result).toEqual({
      ok: true,
      articleId: 7,
      destination: { kind: 'detail', articleId: 7 },
    })
    expect(saveArticle).toHaveBeenCalledOnce()
    expect(saveAdditions).toHaveBeenCalledWith(7)
    expect(saveIngredients).toHaveBeenCalledWith(7)
  })

  it('fails the whole action when a later link step fails', async () => {
    const linkError = new Error('ingredients boom')
    const saveArticle = vi.fn().mockResolvedValue({ id: 7 })
    const saveAdditions = vi.fn().mockResolvedValue(undefined)
    const saveIngredients = vi.fn().mockRejectedValue(linkError)

    const result = await runArticleSaveSequence({
      mode: 'edit',
      isAddition: false,
      ingredientsEnabled: true,
      saveArticle,
      saveAdditions,
      saveIngredients,
    })

    expect(result).toEqual({
      ok: false,
      failedStep: 'ingredients',
      error: linkError,
    })
    expect(saveArticle).toHaveBeenCalledOnce()
    expect(saveAdditions).toHaveBeenCalledOnce()
    expect(saveIngredients).toHaveBeenCalledOnce()
  })

  it('does not run link steps when article persistence fails', async () => {
    const articleError = new Error('article boom')
    const saveArticle = vi.fn().mockRejectedValue(articleError)
    const saveAdditions = vi.fn()
    const saveIngredients = vi.fn()

    const result = await runArticleSaveSequence({
      mode: 'edit',
      isAddition: false,
      ingredientsEnabled: true,
      saveArticle,
      saveAdditions,
      saveIngredients,
    })

    expect(result).toEqual({
      ok: false,
      failedStep: 'article',
      error: articleError,
    })
    expect(saveAdditions).not.toHaveBeenCalled()
    expect(saveIngredients).not.toHaveBeenCalled()
  })
})
