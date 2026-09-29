// The ZONE READ panel is gone from the Trade tab (docs/trade-tab/1-inventory-and-plan.md, U10). Its compact-units
// formatter stays, because the Glass board imports it.

/** Indian-market compact units: crores / lakhs. Sign always shown — these are
 *  day CHANGES, and +0 vs -0 is a real distinction the operator reads.
 *  Exported for the Glass board. */
export const crl = (n: number): string => {
  const a = Math.abs(n)
  const s = n < 0 ? '-' : '+'
  if (a >= 1e7) return `${s}${(a / 1e7).toFixed(2)}Cr`
  if (a >= 1e5) return `${s}${(a / 1e5).toFixed(1)}L`
  return `${s}${a.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}
