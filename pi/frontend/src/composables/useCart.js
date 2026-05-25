import { computed } from 'vue'
import {
  activeTableNumber,
  addCartLine,
  addVoucherCartLine,
  cartLineLabel,
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
    addVoucherCartLine,
    cartLineLabel,
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
