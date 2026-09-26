/** Convert displayed digits only; keep IDs and API payloads unchanged. */
export function persianDigits(value) {
  return String(value ?? '').replace(/[0-9]/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
}
