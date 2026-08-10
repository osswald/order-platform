<template>
  <div class="percent-keypad">
    <div class="display">{{ modelValue }}%</div>
    <div class="keys">
      <button v-for="d in keys" :key="d" type="button" class="key" @click.stop="press(d)">
        {{ d }}
      </button>
    </div>
    <div class="row">
      <button type="button" class="btn" @click.stop="clear">C</button>
      <button type="button" class="btn" @click.stop="back">⌫</button>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: number
  }>(),
  { modelValue: 0 },
)

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']

function press(d: string) {
  const current = Math.max(0, Math.floor(Number(props.modelValue) || 0))
  const next = current === 0 ? Number(d) : current * 10 + Number(d)
  emit('update:modelValue', Math.min(100, next))
}

function clear() {
  emit('update:modelValue', 0)
}

function back() {
  emit('update:modelValue', Math.floor((Number(props.modelValue) || 0) / 10))
}
</script>

<style scoped>
.percent-keypad {
  margin-top: 0.5rem;
}
.display {
  font-size: 1.5rem;
  font-weight: 700;
  text-align: right;
  padding: 0.5rem 0.75rem;
  background: var(--bg);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  font-variant-numeric: tabular-nums;
}
.keys {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.35rem;
}
.key {
  min-height: 48px;
  font-size: 1.15rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  cursor: pointer;
  touch-action: manipulation;
}
.row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.row .btn {
  flex: 1;
}
</style>
