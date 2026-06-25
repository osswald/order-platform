import { ref } from 'vue'
import type { DiscountIn } from '@/types/api'
import type { CartLine } from '@/types/cart'

export const cartLines = ref<CartLine[]>([])
export const orderDiscount = ref<DiscountIn | null>(null)

export function clearCart(): void {
  cartLines.value = []
  orderDiscount.value = null
}

export function setOrderDiscount(discount: DiscountIn | null | undefined): void {
  orderDiscount.value = discount || null
}
