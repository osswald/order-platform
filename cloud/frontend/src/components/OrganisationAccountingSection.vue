<template>
  <div v-if="organisationId" class="org-accounting-section">
    <p v-if="loading" class="muted small">{{ t('organisations.accounting.loading') }}</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>
    <template v-else>
      <section class="accounting-block">
        <h3>{{ t('organisations.vat.sectionTitle') }}</h3>
        <div class="toggle-block">
          <div class="toggle-row">
            <label for="org-vat-liable">{{ t('organisations.vat.vatLiable') }}</label>
            <v-switch
              id="org-vat-liable"
              v-model="vatLiable"
              hide-details
              density="compact"
            />
          </div>
        </div>

        <div v-if="vatLiable" class="form-field">
          <v-select
            v-model="defaultTaxCodeId"
            :items="taxCodeOptions"
            item-title="title"
            item-value="value"
            :label="t('organisations.vat.defaultTaxCode')"
            :loading="taxCodesLoading"
            hide-details="auto"
            required
          />
          <p v-if="taxCodesLoadError" class="error-text small">{{ taxCodesLoadError }}</p>
        </div>
      </section>

      <section class="accounting-block">
        <h3>{{ t('organisations.accounting.sectionTitle') }}</h3>
        <div class="toggle-block">
          <div class="toggle-row">
            <label for="org-accounts-enabled">{{ t('organisations.accounting.accountsEnabled') }}</label>
            <v-switch
              id="org-accounts-enabled"
              v-model="accountsEnabled"
              hide-details
              density="compact"
            />
          </div>
        </div>
        <p class="muted small">{{ t('organisations.accounting.accountsEnabledHint') }}</p>
      </section>

      <template v-if="accountsEnabled">
        <section class="accounting-block">
          <div class="block-header">
            <h3>{{ t('organisations.accounting.accountsTitle') }}</h3>
            <v-btn color="primary" size="small" type="button" @click="openCreateAccount">
              {{ t('organisations.accounting.createAccount') }}
            </v-btn>
          </div>

          <VqDataTable
            :headers="accountHeaders"
            :items="accounts"
            item-value="id"
            class="vq-data-table list-table nested-table"
            hide-default-footer
            :no-data-text="t('organisations.accounting.noAccounts')"
            @click:row="(_e, { item }) => editAccount(item)"
          >
            <template #item.is_default_for_article_categories="{ item }">
              {{ item.is_default_for_article_categories ? t('common.yes') : t('common.no') }}
            </template>
            <template #item.actions="{ item }">
              <v-btn color="error" variant="text" @click.stop="deleteAccount(item.id)">
                {{ t('common.delete') }}
              </v-btn>
            </template>
          </VqDataTable>
          <p v-if="accountsLoadError" class="error-text small">{{ accountsLoadError }}</p>
        </section>

        <section class="accounting-block">
          <h3>{{ t('organisations.accounting.paymentTypeDefaultsTitle') }}</h3>
          <p class="muted small">{{ t('organisations.accounting.paymentTypeDefaultsHint') }}</p>
          <div v-for="row in paymentTypeDefaults" :key="row.payment_type_id" class="default-row">
            <span class="default-label">{{ paymentTypeLabel(row.payment_type_slug) }}</span>
            <v-select
              v-model="row.accounting_account_id"
              :items="accountSelectOptions"
              item-title="title"
              item-value="value"
              :label="t('organisations.accounting.defaultAccount')"
              :placeholder="t('common.optional')"
              hide-details="auto"
              clearable
            />
          </div>
          <div class="actions">
            <v-btn
              color="primary"
              type="button"
              :disabled="savingDefaults"
              :loading="savingDefaults"
              @click="savePaymentTypeDefaults"
            >
              {{ t('organisations.accounting.saveDefaults') }}
            </v-btn>
          </div>
        </section>

        <section class="accounting-block">
          <h3>{{ t('organisations.accounting.taxCodeDefaultsTitle') }}</h3>
          <p class="muted small">{{ t('organisations.accounting.taxCodeDefaultsHint') }}</p>
          <div v-for="row in taxCodeDefaults" :key="row.tax_code_id" class="default-row">
            <span class="default-label">{{ row.tax_code_name }}</span>
            <v-select
              v-model="row.accounting_account_id"
              :items="accountSelectOptions"
              item-title="title"
              item-value="value"
              :label="t('organisations.accounting.defaultAccount')"
              :placeholder="t('common.optional')"
              hide-details="auto"
              clearable
            />
          </div>
          <div class="actions">
            <v-btn
              color="primary"
              type="button"
              :disabled="savingTaxCodeDefaults"
              :loading="savingTaxCodeDefaults"
              @click="saveTaxCodeDefaults"
            >
              {{ t('organisations.accounting.saveDefaults') }}
            </v-btn>
          </div>
        </section>
      </template>

      <div class="actions">
        <v-btn
          color="primary"
          type="button"
          :disabled="saving || !countryId"
          :loading="saving"
          @click="saveOrganisationSettings"
        >
          {{ t('common.save') }}
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <v-dialog v-model="accountDialogVisible" max-width="32rem">
      <v-card>
        <v-card-title>
          {{ accountEditId ? t('organisations.accounting.editAccount') : t('organisations.accounting.createAccount') }}
        </v-card-title>
        <v-card-text>
          <v-form ref="accountFormRef" @submit.prevent="saveAccount">
            <div class="form-field">
              <v-text-field
                v-model="accountForm.name"
                :label="t('common.name')"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </div>
            <div class="form-field">
              <v-text-field
                v-model="accountForm.number"
                :label="t('organisations.accounting.accountNumber')"
                hide-details="auto"
                required
                :rules="[rules.required]"
              />
            </div>
            <v-checkbox
              v-model="accountForm.isDefaultForArticleCategories"
              :label="t('organisations.accounting.defaultForCategories')"
              hide-details
              density="compact"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-btn variant="text" type="button" @click="accountDialogVisible = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-btn color="primary" type="button" :loading="accountSaving" @click="saveAccount">
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, watch, computed, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { parseApiErrorDetail } from '../utils/apiError.js'
import { useTaxCodes } from '../composables/useTaxCodes'
import {
  invalidateAccountingAccountsCache,
  useAccountingAccounts,
} from '../composables/useAccountingAccounts'
import { usePaymentTypes } from '../composables/usePaymentTypes'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

const { t } = useI18n()
const sessionContext = inject(SESSION_CONTEXT_KEY, null)

const props = defineProps({
  organisationId: { type: [Number, String], default: null },
  countryId: { type: [Number, String], default: null },
})

const loading = ref(false)
const loadError = ref('')
const saving = ref(false)
const savingDefaults = ref(false)
const savingTaxCodeDefaults = ref(false)
const message = ref('')
const messageType = ref('')
const vatLiable = ref(false)
const defaultTaxCodeId = ref(null)
const accountsEnabled = ref(false)

const accountDialogVisible = ref(false)
const accountEditId = ref(null)
const accountSaving = ref(false)
const accountFormRef = ref(null)
const accountForm = ref({
  name: '',
  number: '',
  isDefaultForArticleCategories: false,
})

const paymentTypeDefaults = ref([])
const taxCodeDefaults = ref([])

const {
  options: taxCodeOptions,
  loading: taxCodesLoading,
  loadError: taxCodesLoadError,
} = useTaxCodes(() => props.countryId)

const {
  accounts,
  options: accountSelectOptions,
  loading: accountsLoading,
  loadError: accountsLoadError,
  load: reloadAccounts,
} = useAccountingAccounts(() => props.organisationId)

const { paymentTypeLabel } = usePaymentTypes({ activeOnly: true })

const accountHeaders = computed(() => [
  { title: t('organisations.accounting.accountNumber'), key: 'number' },
  { title: t('common.name'), key: 'name' },
  { title: t('organisations.accounting.defaultForCategories'), key: 'is_default_for_article_categories', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

async function loadOrganisation() {
  if (!props.organisationId) return
  loading.value = true
  loadError.value = ''
  message.value = ''
  try {
    const res = await apiFetch(`/organisations/${props.organisationId}`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    vatLiable.value = Boolean(data.vat_liable)
    defaultTaxCodeId.value = data.default_tax_code_id ?? null
    accountsEnabled.value = Boolean(data.accounts_enabled)
  } catch (e) {
    loadError.value = e.message || t('organisations.accounting.loadError')
  } finally {
    loading.value = false
  }
}

async function loadPaymentTypeDefaults() {
  if (!props.organisationId || !accountsEnabled.value) {
    paymentTypeDefaults.value = []
    return
  }
  try {
    const res = await apiFetch(
      `/accounting-accounts/payment-type-defaults?organisation_id=${props.organisationId}`,
    )
    if (!res.ok) throw new Error(await res.text())
    paymentTypeDefaults.value = (await res.json()).map((row) => ({ ...row }))
  } catch {
    paymentTypeDefaults.value = []
  }
}

async function saveOrganisationSettings() {
  if (!props.organisationId) return
  saving.value = true
  message.value = ''
  try {
    const payload = {
      vat_liable: vatLiable.value,
      default_tax_code_id: vatLiable.value ? defaultTaxCodeId.value : null,
      accounts_enabled: accountsEnabled.value,
    }
    const res = await apiFetch(`/organisations/${props.organisationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || t('organisations.accounting.saveError'))
    }
    const data = await res.json()
    vatLiable.value = Boolean(data.vat_liable)
    defaultTaxCodeId.value = data.default_tax_code_id ?? null
    accountsEnabled.value = Boolean(data.accounts_enabled)
    message.value = t('organisations.accounting.saved')
    messageType.value = 'success'
    await sessionContext?.reloadOrganisationsAndSelect?.(Number(props.organisationId))
    if (accountsEnabled.value) {
      await reloadAccounts()
      await loadPaymentTypeDefaults()
    }
  } catch (e) {
    message.value = e.message || t('organisations.accounting.saveError')
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

function openCreateAccount() {
  accountEditId.value = null
  accountForm.value = {
    name: '',
    number: '',
    isDefaultForArticleCategories: false,
  }
  accountDialogVisible.value = true
}

function editAccount(account) {
  accountEditId.value = account.id
  accountForm.value = {
    name: account.name || '',
    number: account.number || '',
    isDefaultForArticleCategories: Boolean(account.is_default_for_article_categories),
  }
  accountDialogVisible.value = true
}

async function saveAccount() {
  if (!(await validateForm(accountFormRef))) return
  accountSaving.value = true
  try {
    const payload = {
      name: accountForm.value.name,
      number: accountForm.value.number,
      is_default_for_article_categories: accountForm.value.isDefaultForArticleCategories,
    }
    const path = accountEditId.value
      ? `/accounting-accounts/${accountEditId.value}`
      : '/accounting-accounts/'
    const method = accountEditId.value ? 'PUT' : 'POST'
    if (!accountEditId.value) {
      payload.organisation_id = Number(props.organisationId)
    }
    const res = await apiFetch(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('organisations.accounting.accountSaveError'))
    }
    invalidateAccountingAccountsCache(props.organisationId)
    await reloadAccounts()
    await loadPaymentTypeDefaults()
    accountDialogVisible.value = false
    message.value = t('organisations.accounting.accountSaved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.accounting.accountSaveError')
    messageType.value = 'error'
  } finally {
    accountSaving.value = false
  }
}

async function deleteAccount(accountId) {
  if (!confirm(t('organisations.accounting.deleteConfirm'))) return
  try {
    const res = await apiFetch(`/accounting-accounts/${accountId}`, { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('organisations.accounting.accountDeleteError'))
    }
    invalidateAccountingAccountsCache(props.organisationId)
    await reloadAccounts()
    await loadPaymentTypeDefaults()
    message.value = t('organisations.accounting.accountDeleted')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.accounting.accountDeleteError')
    messageType.value = 'error'
  }
}

async function loadTaxCodeDefaults() {
  if (!props.organisationId || !accountsEnabled.value) {
    taxCodeDefaults.value = []
    return
  }
  try {
    const res = await apiFetch(
      `/accounting-accounts/tax-code-defaults?organisation_id=${props.organisationId}`,
    )
    if (!res.ok) throw new Error(await res.text())
    taxCodeDefaults.value = (await res.json()).map((row) => ({ ...row }))
  } catch {
    taxCodeDefaults.value = []
  }
}

async function saveTaxCodeDefaults() {
  if (!props.organisationId) return
  savingTaxCodeDefaults.value = true
  message.value = ''
  try {
    const res = await apiFetch(
      `/accounting-accounts/tax-code-defaults?organisation_id=${props.organisationId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          defaults: taxCodeDefaults.value.map((row) => ({
            tax_code_id: row.tax_code_id,
            accounting_account_id: row.accounting_account_id ?? null,
          })),
        }),
      },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('organisations.accounting.defaultsSaveError'))
    }
    taxCodeDefaults.value = await res.json()
    message.value = t('organisations.accounting.defaultsSaved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.accounting.defaultsSaveError')
    messageType.value = 'error'
  } finally {
    savingTaxCodeDefaults.value = false
  }
}

async function savePaymentTypeDefaults() {
  if (!props.organisationId) return
  savingDefaults.value = true
  message.value = ''
  try {
    const payload = {
      defaults: paymentTypeDefaults.value.map((row) => ({
        payment_type_id: row.payment_type_id,
        accounting_account_id: row.accounting_account_id ?? null,
      })),
    }
    const res = await apiFetch(
      `/accounting-accounts/payment-type-defaults?organisation_id=${props.organisationId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(parseApiErrorDetail(err.detail) || t('organisations.accounting.defaultsSaveError'))
    }
    paymentTypeDefaults.value = (await res.json()).map((row) => ({ ...row }))
    message.value = t('organisations.accounting.defaultsSaved')
    messageType.value = 'success'
  } catch (e) {
    message.value = e.message || t('organisations.accounting.defaultsSaveError')
    messageType.value = 'error'
  } finally {
    savingDefaults.value = false
  }
}

watch(
  () => [props.organisationId, props.countryId],
  async () => {
    await loadOrganisation()
    if (accountsEnabled.value) {
      await loadPaymentTypeDefaults()
      await loadTaxCodeDefaults()
    }
  },
  { immediate: true },
)

watch(accountsEnabled, async (enabled) => {
  if (!enabled) {
    paymentTypeDefaults.value = []
    return
  }
  await reloadAccounts()
  await loadPaymentTypeDefaults()
})

watch(vatLiable, (enabled) => {
  if (!enabled) {
    defaultTaxCodeId.value = null
  }
})
</script>

<style scoped>
.org-accounting-section {
  max-width: 40rem;
}

.accounting-block {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.accounting-block:last-of-type {
  border-bottom: none;
}

.accounting-block h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
}

.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.block-header h3 {
  margin: 0;
}

.toggle-block {
  margin-bottom: 0.75rem;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.toggle-row label {
  font-weight: 500;
}

.form-field {
  margin-bottom: 1rem;
}

.default-row {
  display: grid;
  grid-template-columns: minmax(8rem, 40%) 1fr;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.default-label {
  font-weight: 500;
}

.actions {
  margin-top: 1rem;
}

.error-text {
  color: rgb(var(--v-theme-error));
}

.error-text.small {
  margin-top: 0.35rem;
  font-size: 0.875rem;
}

.success {
  color: rgb(var(--v-theme-success));
}
</style>
