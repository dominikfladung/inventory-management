<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        <span class="budget-value">{{ money(budget) }}</span>
      </div>
      <div class="slider-wrap">
        <input
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          max="500000"
          step="5000"
          :aria-label="t('restocking.budgetSlider')"
        />
        <div class="slider-scale">
          <span>{{ money(0) }}</span>
          <span>{{ money(500000) }}</span>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.budget') }}</div>
        <div class="stat-value">{{ money(budget) }}</div>
      </div>
      <div :class="['stat-card', overBudget ? 'danger' : 'success']">
        <div class="stat-label">{{ t('restocking.orderTotal') }}</div>
        <div class="stat-value">{{ money(orderTotal) }}</div>
      </div>
      <div :class="['stat-card', remaining < 0 ? 'danger' : 'warning']">
        <div class="stat-label">{{ t('restocking.remaining') }}</div>
        <div class="stat-value">{{ money(remaining) }}</div>
      </div>
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.orderLeadTime') }}</div>
        <div class="stat-value">{{ t('restocking.days', { count: orderLeadTime }) }}</div>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ rows.length }})</h3>
      </div>
      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="rows.length === 0" class="empty-state">{{ t('restocking.noItems') }}</div>
      <div v-else class="table-container">
        <table>
          <thead>
            <tr>
              <th>{{ t('restocking.table.sku') }}</th>
              <th>{{ t('restocking.table.name') }}</th>
              <th>{{ t('restocking.table.quantity') }}</th>
              <th>{{ t('restocking.table.unitCost') }}</th>
              <th>{{ t('restocking.table.lineTotal') }}</th>
              <th>{{ t('restocking.table.supplier') }}</th>
              <th>{{ t('restocking.table.leadTime') }}</th>
              <th>{{ t('restocking.table.trend') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.sku">
              <td>
                <strong>{{ row.sku }}</strong>
              </td>
              <td>{{ translateProductName(row.name) }}</td>
              <td>
                <input
                  v-model.number="row.quantity"
                  type="number"
                  min="1"
                  step="1"
                  :class="['qty-input', { invalid: !isValidQty(row.quantity) }]"
                  :aria-label="t('restocking.table.quantity')"
                />
              </td>
              <td>{{ money(row.unit_cost) }}</td>
              <td>
                <strong>{{ money(lineTotal(row)) }}</strong>
              </td>
              <td>{{ row.supplier }}</td>
              <td>{{ row.lead_time_days }}</td>
              <td>
                <span :class="['badge', trendClass(row.trend)]">{{ trendLabel(row.trend) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="order-actions">
        <div v-if="overBudget" class="warning-text">{{ t('restocking.overBudget') }}</div>
        <div v-else-if="!allQuantitiesValid" class="warning-text">
          {{ t('restocking.invalidQuantity') }}
        </div>
        <div v-if="successMessage" class="success-text">{{ successMessage }}</div>
        <div v-if="submitError" class="error-text">{{ submitError }}</div>
        <button class="place-order-btn" :disabled="!canSubmit" @click="submitOrder">
          {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, translateProductName } = useI18n()

    // Source data is USD; always display USD regardless of locale
    const money = (v) =>
      '$' +
      Number(v).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })

    const budget = ref(100000)
    const rows = ref([])
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)
    const successMessage = ref(null)

    let debounceTimer = null
    let requestId = 0

    const isValidQty = (q) => Number.isInteger(q) && q >= 1
    const lineTotal = (row) => (isValidQty(row.quantity) ? row.quantity * row.unit_cost : 0)

    const orderTotal = computed(() => rows.value.reduce((sum, r) => sum + lineTotal(r), 0))
    const remaining = computed(() => budget.value - orderTotal.value)
    const toCents = (v) => Math.round(Number(v) * 100)
    const overBudget = computed(() => toCents(orderTotal.value) > toCents(budget.value))
    const orderLeadTime = computed(() =>
      rows.value.reduce((max, r) => Math.max(max, r.lead_time_days || 0), 0)
    )
    const allQuantitiesValid = computed(() => rows.value.every((r) => isValidQty(r.quantity)))
    const pending = ref(false) // debounce pending
    const canSubmit = computed(
      () =>
        rows.value.length > 0 &&
        allQuantitiesValid.value &&
        !overBudget.value &&
        !submitting.value &&
        !loading.value &&
        !pending.value &&
        !error.value
    )

    const loadRecommendations = async () => {
      const myId = ++requestId
      pending.value = false
      try {
        loading.value = true
        error.value = null
        const data = await api.getRestockRecommendations(budget.value)
        if (myId !== requestId) return
        rows.value = data.items.map((item) => ({ ...item }))
      } catch (err) {
        if (myId !== requestId) return
        error.value = t('restocking.loadError') + ': ' + err.message
        rows.value = []
      } finally {
        if (myId === requestId) loading.value = false
      }
    }

    watch(budget, () => {
      successMessage.value = null
      submitError.value = null
      clearTimeout(debounceTimer)
      pending.value = true
      debounceTimer = setTimeout(loadRecommendations, 250)
    })

    const formatDate = (dateString) => {
      const d = new Date(dateString)
      if (isNaN(d.getTime())) return dateString
      return d.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const submitOrder = async () => {
      if (!canSubmit.value || submitting.value) return
      submitting.value = true
      submitError.value = null
      successMessage.value = null
      try {
        const order = await api.placeRestockOrder({
          budget: budget.value,
          items: rows.value.map((r) => ({ sku: r.sku, quantity: r.quantity }))
        })
        // Prevent resubmission: clear the table until budget changes / reload
        rows.value = []
        successMessage.value = t('restocking.success', {
          id: order.id,
          date: formatDate(order.expected_delivery)
        })
      } catch (err) {
        const detail = err.response && err.response.data && err.response.data.detail
        const text =
          typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : err.message
        submitError.value = t('restocking.failure') + ': ' + text
      } finally {
        submitting.value = false
      }
    }

    const trendClass = (trend) => {
      const key = String(trend || '').toLowerCase()
      return ['increasing', 'decreasing', 'stable'].includes(key) ? key : 'info'
    }

    const trendLabel = (trend) => {
      const key = String(trend || '').toLowerCase()
      return ['increasing', 'decreasing', 'stable'].includes(key)
        ? t(`restocking.trend.${key}`)
        : trend
    }

    onMounted(loadRecommendations)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      money,
      budget,
      rows,
      loading,
      error,
      submitting,
      submitError,
      successMessage,
      orderTotal,
      remaining,
      overBudget,
      orderLeadTime,
      allQuantitiesValid,
      canSubmit,
      isValidQty,
      lineTotal,
      submitOrder,
      trendClass,
      trendLabel,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
}

.slider-wrap {
  padding: 0.5rem 0 0.25rem;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #0f172a;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.budget-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #0f172a;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.budget-slider:focus-visible::-webkit-slider-thumb {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.qty-input {
  width: 90px;
  padding: 0.375rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #0f172a;
}

.qty-input.invalid {
  border-color: #ef4444;
  background: #fef2f2;
}

.empty-state {
  padding: 1.5rem;
  color: #64748b;
  text-align: center;
}

.order-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
  padding: 1rem 0 0.25rem;
}

.place-order-btn {
  padding: 0.625rem 1.5rem;
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.warning-text {
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.success-text {
  color: #166534;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.error-text {
  color: #991b1b;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}
</style>
