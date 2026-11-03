import { describe, expect, it } from 'vitest'
import { convertAmount, formatCurrency, formatCurrencyWithDecimals } from './currency'

describe('currency utils', () => {
  it('formats USD without decimals', () => {
    expect(formatCurrency(1234.56)).toBe('$1,235')
  })

  it('converts and formats JPY', () => {
    expect(formatCurrency(100, 'JPY')).toBe('¥15,000')
  })

  it('formats USD with the requested decimals', () => {
    expect(formatCurrencyWithDecimals(1234.5, 'USD', 2)).toBe('$1,234.50')
  })

  it('converts amounts only for JPY', () => {
    expect(convertAmount(10)).toBe(10)
    expect(convertAmount(10, 'JPY')).toBe(1500)
  })
})
