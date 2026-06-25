import { computed } from 'vue'
import { toast } from '@/store'

export function useToast() {
  return {
    toast: computed(() => toast.value),
  }
}
