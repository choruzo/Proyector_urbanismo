/**
 * Utilidades de formato para números y divisas en el dashboard.
 */

/** Formatea un número con separadores de miles (ej: 1.234.567) */
export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value == null || isNaN(value)) return '—'
  return new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/** Formatea una cantidad en euros (ej: 1.234.567 €) */
export function formatCurrency(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—'
  if (value >= 1_000_000) {
    return `${formatNumber(value / 1_000_000, 2)} M€`
  }
  if (value >= 1_000) {
    return `${formatNumber(value / 1_000, 1)} K€`
  }
  return `${formatNumber(value, 0)} €`
}

/** Formatea un porcentaje con signo (ej: +12.5%) */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNumber(value, 1)}%`
}
