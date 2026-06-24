import { ref } from 'vue'

/** @type {import('vue').Ref<Array<{ lineId: string, article_id: number, qty: number, station_uuid: string | null, note: string }>>} */
export const cartLines = ref([])

/** @type {import('vue').Ref<{ kind: 'percent' | 'amount', value: number } | null>} */
export const orderDiscount = ref(null)

export function clearCart() {
  cartLines.value = []
  orderDiscount.value = null
}

export function setOrderDiscount(discount) {
  orderDiscount.value = discount || null
}
