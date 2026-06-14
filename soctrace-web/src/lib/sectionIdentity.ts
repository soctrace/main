export function normalizeSectionId(id: string | number): string {
  const value = String(id).trim();

  if (/^\d+$/.test(value) && value.length < 10) {
    return value.padStart(2, "0");
  }

  return value;
}
