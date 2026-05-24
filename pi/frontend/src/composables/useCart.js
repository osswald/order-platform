import { computed } from 'vue'
import {
  activeTableNumber,
  addCartLine,
  additionsSignature,
  articleName,
  availableAdditionQty,
  availableQty,
  cartCount,
  cartLines,
  cartTotalCents,
  clearCart,
  decrementCartLine,
  getArticle,
  removeCartLine,
  updateCartLine,
} from '../store'

export function useCart() {
  return {
    cartLines: computed(() => cartLines.value),
    lines: computed(() => cartLines.value),
    cartCount,
    cartTotalCents,
    totalCents: cartTotalCents,
    activeTableNumber,
    addCartLine,
    removeCartLine,
    clearCart,
    decrementCartLine,
    updateCartLine,
    availableQty,
    availableAdditionQty,
    getArticle,
    articleName,
    additionsSignature,
  }
}
