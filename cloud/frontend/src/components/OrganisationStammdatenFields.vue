<template>
  <div class="form-field">
    <v-text-field
      v-model="form.name"
      :label="$t('common.name')"
      :placeholder="$t('organisations.namePlaceholder')"
      hide-details="auto"
      required
      :rules="[rules.required]"
    />
  </div>
  <div class="form-field">
    <v-text-field
      v-model="form.address"
      :label="$t('common.address')"
      :placeholder="$t('organisations.addressPlaceholder')"
      hide-details="auto"
    />
  </div>
  <div class="field-row">
    <div class="form-field">
      <v-text-field
        v-model="form.zip"
        :label="$t('common.zip')"
        :placeholder="$t('organisations.zipPlaceholder')"
        hide-details="auto"
      />
    </div>
    <div class="form-field">
      <v-text-field
        v-model="form.city"
        :label="$t('common.city')"
        :placeholder="$t('organisations.cityPlaceholder')"
        hide-details="auto"
      />
    </div>
  </div>
  <div class="form-field">
    <v-select
      v-model="form.country"
      :items="countryOptions"
      :label="$t('common.country')"
      :placeholder="$t('organisations.selectCountry')"
      hide-details="auto"
      required
      :rules="[rules.required]"
    />
  </div>
  <div class="form-field">
    <v-select
      v-model="form.currency"
      :items="currencyOptions"
      :label="$t('organisations.currency')"
      :placeholder="$t('organisations.currencyPlaceholder')"
      hide-details="auto"
      required
      :rules="[rules.required]"
    />
  </div>
  <div class="form-field">
    <label>{{ $t('common.users') }}</label>
    <UserPicker v-model="form.userIdsArray" />
    <small>{{ $t('organisations.usersHint') }}</small>
  </div>
</template>

<script setup>
import UserPicker from './UserPicker.vue'
import { rules } from '../utils/formRules.js'

defineProps({
  form: {
    type: Object,
    required: true,
  },
  countryOptions: {
    type: Array,
    required: true,
  },
  currencyOptions: {
    type: Array,
    required: true,
  },
})
</script>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small {
  color: rgba(var(--v-theme-on-surface), 0.65);
}

@media (max-width: 1000px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
