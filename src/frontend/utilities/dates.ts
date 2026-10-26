export function todayInZone(timezone: string, clock = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(clock);
  const part = (name: string) =>
    parts.find((value) => value.type === name)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}
